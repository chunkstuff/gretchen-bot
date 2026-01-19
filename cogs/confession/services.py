"""
Business logic for confession scheduling and posting.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict
from .embeds import create_posted_confession_embed

logger = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")


class ConfessionService:
	"""Handles confession scheduling and posting logic."""

	def __init__(self, bot, data_manager, posting_channel_id: int, intros: list):
		"""
		Initialize the confession service.

		Args:
			bot: The Discord bot instance
			data_manager: The ConfessionData instance
			posting_channel_id: Channel ID for posting confessions
			intros: List of intro messages for confessions
		"""
		self.bot = bot
		self.data = data_manager
		self.posting_channel_id = posting_channel_id
		self.intros = intros
		self.scheduled_tasks = {}

	def get_next_2am_uk(self) -> datetime:
		"""
		Get the next available posting time slot (12am, 1am, 2am, or 3am UK).

		Returns:
			datetime: Next available posting time
		"""
		now_uk = datetime.now(UK_TZ)
		posting_hours = [0, 1, 2, 3]  # 12am, 1am, 2am, 3am

		# Get all currently scheduled times (not just dates)
		scheduled_times = set()
		for confession in self.data.post_queue:
			if confession.get("scheduled_time"):
				scheduled_dt = datetime.fromisoformat(confession["scheduled_time"])
				if scheduled_dt.tzinfo is None:
					scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
				scheduled_dt_uk = scheduled_dt.astimezone(UK_TZ)
				scheduled_times.add(scheduled_dt_uk)

		# Try to find next available slot
		days_ahead = 0
		while days_ahead < 365:  # Safety limit
			for hour in posting_hours:
				candidate = now_uk.replace(
					hour=hour,
					minute=0,
					second=0,
					microsecond=0
				) + timedelta(days=days_ahead)

				# Skip if this time has already passed today
				if candidate <= now_uk:
					continue

				# Check if this slot is available
				if candidate not in scheduled_times:
					return candidate

			days_ahead += 1

		# Fallback (should never reach here)
		return now_uk + timedelta(days=1)

	def schedule_confession_post(self, confession: Dict):
		"""
		Schedule a confession to be posted at its designated time.

		Args:
			confession: The confession dict to schedule
		"""
		confession_id = confession["id"]

		# Cancel any existing task for this confession
		if confession_id in self.scheduled_tasks:
			self.scheduled_tasks[confession_id].cancel()
			logger.info(
				"Cancelled existing task for Confession #%s",
				confession_id
			)

		# Create a new task to post the confession at the scheduled time
		task = asyncio.create_task(self._wait_and_post_confession(confession))
		self.scheduled_tasks[confession_id] = task
		logger.info(
			"Scheduled Confession #%s for %s",
			confession_id,
			confession['scheduled_time']
		)

	async def _wait_and_post_confession(self, confession: Dict):
		"""
		Wait until the scheduled time and then post the confession.

		Args:
			confession: The confession dict to post
		"""
		try:
			scheduled_time = datetime.fromisoformat(confession["scheduled_time"])
			now = datetime.now(timezone.utc)

			# Calculate how long to wait
			wait_seconds = (scheduled_time - now).total_seconds()

			if wait_seconds > 0:
				logger.info(
					"Waiting %.0f seconds (%.1f hours) to post Confession #%s",
					wait_seconds,
					wait_seconds/3600,
					confession['id']
				)
				await asyncio.sleep(wait_seconds)
			else:
				logger.warning(
					"Confession #%s is overdue by %.0f seconds. Posting immediately.",
					confession['id'],
					abs(wait_seconds)
				)

			# Post the confession
			await self.post_confession(confession)

		except asyncio.CancelledError:
			logger.info(
				"Scheduled task for Confession #%s was cancelled",
				confession['id']
			)
			raise
		except Exception as e:
			logger.error(
				"Error in _wait_and_post_confession for Confession #%s: %s",
				confession['id'],
				e,
				exc_info=True
			)

	async def post_confession(self, confession: Dict):
		"""
		Post a confession to the designated channel.

		Args:
			confession: The confession dict to post
		"""
		logger.info("Posting confession #%s", confession['id'])

		confession_channel = self.bot.get_channel(self.posting_channel_id)
		if not confession_channel:
			logger.error(
				"Posting channel with ID %s not found or inaccessible",
				self.posting_channel_id
			)
			return

		try:
			intro_message = random.choice(self.intros)
			embed = create_posted_confession_embed(confession, intro_message)
			await confession_channel.send(embed=embed)
			logger.info("Confession #%s posted successfully", confession['id'])

			# Archive and remove from queue
			self.data.archive(confession)
			self.data.remove_from_post_queue(confession)

			# Remove from scheduled tasks
			if confession['id'] in self.scheduled_tasks:
				del self.scheduled_tasks[confession['id']]

		except Exception as e:
			logger.error(
				"Failed to post confession #%s: %s",
				confession['id'],
				e,
				exc_info=True
			)

	async def reschedule_pending_confessions(self):
		"""Reschedule all confessions in the post queue on bot startup."""
		now = datetime.now(timezone.utc)
		overdue_count = 0
		scheduled_count = 0

		logger.info(
			"Rescheduling %s pending confessions from post queue",
			len(self.data.post_queue)
		)

		# Create a copy to iterate safely
		for confession in self.data.post_queue[:]:
			if not confession.get("scheduled_time"):
				logger.warning(
					"Confession #%s has no scheduled_time. Skipping.",
					confession['id']
				)
				continue

			scheduled_time = datetime.fromisoformat(confession["scheduled_time"])

			# If the scheduled time has already passed, post immediately
			if scheduled_time <= now:
				overdue_count += 1
				logger.info(
					"Confession #%s is overdue (scheduled for %s). Posting immediately.",
					confession['id'],
					confession['scheduled_time']
				)
				await self.post_confession(confession)
			else:
				# Schedule the confession for its designated time
				scheduled_count += 1
				self.schedule_confession_post(confession)

		logger.info(
			"Rescheduling complete: %s scheduled, %s posted immediately",
			scheduled_count,
			overdue_count
		)

	def cancel_all_tasks(self):
		"""Cancel all scheduled posting tasks."""
		for confession_id, task in self.scheduled_tasks.items():
			task.cancel()
			logger.debug("Cancelled task for Confession #%s", confession_id)
		self.scheduled_tasks.clear()
		logger.info("All scheduled confession tasks cancelled")
