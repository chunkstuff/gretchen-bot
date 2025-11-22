"""
Business logic for confession scheduling and posting.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Optional

import discord

logger = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")


class ConfessionService:
	"""Handles confession scheduling and posting logic."""
	
	def __init__(self, bot, data_manager, posting_channel_id: int, intros: list):
		self.bot = bot
		self.data = data_manager
		self.posting_channel_id = posting_channel_id
		self.intros = intros
		self.scheduled_tasks = {}  # Dictionary to track scheduled posting tasks
		
	def get_next_2am_uk(self) -> datetime:
		"""Get the next available 2am UK time slot that isn't already scheduled."""
		now_uk = datetime.now(UK_TZ)
		
		# Start with tomorrow at 2am UK time
		next_2am = (now_uk + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
		
		# If we haven't passed 2am today yet, use today
		today_2am = now_uk.replace(hour=2, minute=0, second=0, microsecond=0)
		if now_uk < today_2am:
			next_2am = today_2am
		
		# Get all scheduled dates
		scheduled_dates = self.data.get_scheduled_dates()
		
		# Find the next available date
		while next_2am.date() in scheduled_dates:
			next_2am += timedelta(days=1)
		
		return next_2am
		
	def schedule_confession_post(self, confession: Dict):
		"""Schedule a confession to be posted at its designated time."""
		confession_id = confession["id"]
		
		# Cancel any existing task for this confession
		if confession_id in self.scheduled_tasks:
			self.scheduled_tasks[confession_id].cancel()
			logger.info(f"Cancelled existing task for Confession #{confession_id}")
		
		# Create a new task to post the confession at the scheduled time
		task = asyncio.create_task(self._wait_and_post_confession(confession))
		self.scheduled_tasks[confession_id] = task
		logger.info(f"Scheduled Confession #{confession_id} for {confession['scheduled_time']}")
		
	async def _wait_and_post_confession(self, confession: Dict):
		"""Wait until the scheduled time and then post the confession."""
		try:
			scheduled_time = datetime.fromisoformat(confession["scheduled_time"])
			now = datetime.now(timezone.utc)
			
			# Calculate how long to wait
			wait_seconds = (scheduled_time - now).total_seconds()
			
			if wait_seconds > 0:
				logger.info(f"Waiting {wait_seconds:.0f} seconds ({wait_seconds/3600:.1f} hours) to post Confession #{confession['id']}")
				await asyncio.sleep(wait_seconds)
			else:
				logger.warning(f"Confession #{confession['id']} is overdue by {abs(wait_seconds):.0f} seconds. Posting immediately.")
			
			# Post the confession
			await self.post_confession(confession)
			
		except asyncio.CancelledError:
			logger.info(f"Scheduled task for Confession #{confession['id']} was cancelled")
			raise
		except Exception as e:
			logger.error(f"Error in _wait_and_post_confession for Confession #{confession['id']}: {e}", exc_info=True)
			
	async def post_confession(self, confession: Dict):
		"""Post a confession to the designated channel."""
		logger.info(f"Posting confession #{confession['id']}")
		
		confession_channel = self.bot.get_channel(self.posting_channel_id)
		if not confession_channel:
			logger.error(f"Posting channel with ID {self.posting_channel_id} not found or inaccessible")
			return
		
		try:
			confession_message = random.choice(self.intros)
			embed = discord.Embed(
				title=f"Confession #{confession['id']}",
				description=f"{confession_message}\n```\n{confession['text']}\n```",
				color=0xFFC0CB,
				timestamp=datetime.fromisoformat(confession["submission_time"]),
			)
			embed.add_field(name="", value="🤫🤭")
			embed.set_footer(text="Anonymously Submitted")
			await confession_channel.send(embed=embed)
			logger.info(f"Confession #{confession['id']} posted successfully")
			
			# Archive and remove from queue
			self.data.archive(confession)
			self.data.remove_from_post_queue(confession)
			
			# Remove from scheduled tasks
			if confession['id'] in self.scheduled_tasks:
				del self.scheduled_tasks[confession['id']]
				
		except Exception as e:
			logger.error(f"Failed to post confession #{confession['id']}: {e}", exc_info=True)
			
	async def reschedule_pending_confessions(self):
		"""Reschedule all confessions in the post queue (called on bot startup)."""
		now = datetime.now(timezone.utc)
		overdue_count = 0
		scheduled_count = 0
		
		logger.info(f"Rescheduling {len(self.data.post_queue)} pending confessions from post queue")
		
		for confession in self.data.post_queue[:]:  # Create a copy to iterate safely
			if not confession.get("scheduled_time"):
				logger.warning(f"Confession #{confession['id']} has no scheduled_time. Skipping.")
				continue
				
			scheduled_time = datetime.fromisoformat(confession["scheduled_time"])
			
			# If the scheduled time has already passed, post immediately
			if scheduled_time <= now:
				overdue_count += 1
				logger.info(f"Confession #{confession['id']} is overdue (scheduled for {confession['scheduled_time']}). Posting immediately.")
				await self.post_confession(confession)
			else:
				# Schedule the confession for its designated time
				scheduled_count += 1
				self.schedule_confession_post(confession)
				
		logger.info(f"Rescheduling complete: {scheduled_count} scheduled, {overdue_count} posted immediately")
		
	def cancel_all_tasks(self):
		"""Cancel all scheduled posting tasks."""
		for confession_id, task in self.scheduled_tasks.items():
			task.cancel()
			logger.debug(f"Cancelled task for Confession #{confession_id}")
		self.scheduled_tasks.clear()
		logger.info("All scheduled confession tasks cancelled")