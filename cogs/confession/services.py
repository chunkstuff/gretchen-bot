"""
Business logic for confession scheduling and posting.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict
from .embeds import create_posted_confession_embed

logger = logging.getLogger(__name__)


def next_post_time(now: datetime) -> datetime:
	"""
	Return the next :15-past-the-hour after `now`.

	timedelta carries hour/day/month/year rollover, so month lengths,
	leap years and new year need no special cases.

	Args:
		now: The current time

	Returns:
		datetime: The next posting time, strictly after `now`
	"""
	next_run = now.replace(minute=15, second=0, microsecond=0)
	if now.minute >= 15:
		next_run += timedelta(hours=1)
	return next_run


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
		self.posting_task = None

	async def start_hourly_posting(self):
		"""Start the hourly posting task that runs at :15 past each hour."""
		if self.posting_task and not self.posting_task.done():
			logger.warning("Hourly posting task already running")
			return

		self.posting_task = asyncio.create_task(self._hourly_posting_loop())
		logger.info("Started hourly posting task")

	async def _hourly_posting_loop(self):
		"""Run posting loop that posts confessions at :15 past each hour."""
		while True:
			try:
				# Calculate next :15 past the hour
				now = datetime.now(timezone.utc)
				next_run = next_post_time(now)

				wait_seconds = (next_run - now).total_seconds()
				logger.info(
					"Next confession post at %s (in %.0f seconds)",
					next_run.strftime("%Y-%m-%d %H:%M UTC"),
					wait_seconds
				)

				# Wait until :15 past the hour
				await asyncio.sleep(wait_seconds)

				# Post next confession if queue has items
				if self.data.post_queue:
					confession = self.data.post_queue[0]
					await self.post_confession(confession)
				else:
					logger.info("No confessions in queue to post")

			except asyncio.CancelledError:
				logger.info("Hourly posting task cancelled")
				raise
			except Exception as e:
				logger.error(
					"Error in hourly posting loop: %s",
					e,
					exc_info=True
				)
				# Wait a bit before retrying to avoid spam
				await asyncio.sleep(60)

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

		except Exception as e:
			logger.error(
				"Failed to post confession #%s: %s",
				confession['id'],
				e,
				exc_info=True
			)

	def stop_posting(self):
		"""Stop the hourly posting task."""
		if self.posting_task and not self.posting_task.done():
			self.posting_task.cancel()
			logger.info("Stopped hourly posting task")
