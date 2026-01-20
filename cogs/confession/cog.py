"""
Main confession cog - coordinates between data, services, and views.
"""
import logging
import asyncio
import discord
from discord.ext import commands

from config import (
	EMBED_CHANNEL_ID,
	POSTING_CHANNEL_ID,
	MODERATOR_CHANNEL_ID,
	PERSISTENCE_FILE,
	ARCHIVE_FILE
)
from data.intros import intros
from .models import ConfessionData
from .services import ConfessionService
from .views import ConfessionNotificationView, PersistentView

logger = logging.getLogger(__name__)


class ConfessionCog(commands.Cog):
	"""Main cog for handling confessions."""

	def __init__(self, bot):
		"""
		Initialize the confession cog.

		Args:
			bot: The Discord bot instance
		"""
		self.bot = bot

		# Configuration
		self.embed_channel_id = EMBED_CHANNEL_ID
		self.posting_channel_id = POSTING_CHANNEL_ID
		self.moderator_channel_id = MODERATOR_CHANNEL_ID

		# Initialize data layer
		self.data = ConfessionData(PERSISTENCE_FILE, ARCHIVE_FILE)
		self.data.load()

		# Initialize service layer
		self.service = ConfessionService(bot, self.data, POSTING_CHANNEL_ID, intros)

	@commands.Cog.listener()
	async def on_ready(self):
		"""Initialize when bot is ready."""
		logger.info("ConfessionCog initializing...")

		# Update or create the confession embed
		await self.update_confession_embed()

		# Reattach views to existing moderation messages
		await self.fetch_pending_moderation_messages()

		# Start the hourly posting task
		await self.service.start_hourly_posting()

		logger.info("ConfessionCog is ready!")

	@commands.Cog.listener()
	async def on_interaction(self, interaction: discord.Interaction):
		"""
		Log interactions related to the main confession embed.

		Args:
			interaction: The Discord interaction to log
		"""
		if interaction.type != discord.InteractionType.component:
			return

		if interaction.message and interaction.message.id == self.data.embed_message_id:
			logger.info(
				"Interaction on confession embed: %s by %s (%s)",
				interaction.data.get('custom_id'),
				interaction.user,
				interaction.user.id
			)

	async def update_confession_embed(self):
		"""Update or recreate the confession embed message."""
		try:
			channel = self.bot.get_channel(self.embed_channel_id)
			if not channel:
				logger.error("Embed channel not found. Check the EMBED_CHANNEL_ID.")
				return

			# Try to fetch and update existing message
			if self.data.embed_message_id:
				try:
					message = await channel.fetch_message(self.data.embed_message_id)
					logger.info("Found existing confession embed. Updating...")

					embed = self._create_embed()
					view = PersistentView(self)

					await message.edit(embed=embed, view=view)
					logger.info("Confession embed updated successfully.")
					return

				except discord.NotFound:
					logger.warning("Embed message ID is invalid. Recreating the embed...")

			# Create new embed if not found or message ID is invalid
			embed = self._create_embed()
			view = PersistentView(self)
			message = await channel.send(embed=embed, view=view)

			# Save the new message ID
			self.data.embed_message_id = message.id
			self.data.save()
			logger.info("New confession embed created and message ID updated.")

		except discord.Forbidden:
			logger.error(
				"Bot lacks permissions to access the channel or edit the message."
			)
		except discord.HTTPException as http_err:
			logger.error(
				"HTTPException occurred while updating confession embed: %s",
				http_err
			)
		except Exception as e:
			logger.error(
				"Unexpected error during confession embed update: %s",
				e,
				exc_info=True
			)

	def _create_embed(self):
		"""
		Create the confession embed.

		Returns:
			discord.Embed: The main confession submission embed
		"""
		return discord.Embed(
			title="Whisper to Gretchen",
			description=(
				"🤫 Babe, you can, like, totally tell me *anything*, "
				"it's **completely anonymous** "
				"and **nobody will ever know it was you**, like, not even me, "
				"and it'll just be between us "
				"unless it's, like, super juicy and I just have to share it "
				"because, I mean, come on, like that "
				"time Dawn Schweitzer told me her parents were out of town "
				"and she threw a rager, but then guess what? "
				"She got grounded for, like, a *month* "
				"because the neighbors called the cops—ugh, so tragic—"
				"but don't worry, you're safe with me, promise! 💋✨"
			),
			color=0xFFC0CB,
		)

	async def fetch_pending_moderation_messages(self):
		"""Rebuild moderation views for unapproved confessions."""
		mod_channel = self.bot.get_channel(self.moderator_channel_id)
		if not mod_channel:
			logger.error("Moderation channel not found.")
			return

		logger.info(
			"Reattaching views to %s pending moderation messages",
			len(self.data.submission_queue)
		)

		for confession in self.data.submission_queue:
			if confession["message_id"]:
				try:
					message = await mod_channel.fetch_message(confession["message_id"])
					view = ConfessionNotificationView(self, confession)
					await message.edit(view=view)
					logger.info(
						"Reattached view to moderation message for Confession #%s",
						confession['id']
					)
					await asyncio.sleep(0.5)
				except discord.NotFound:
					logger.warning(
						"Moderation message for Confession #%s not found",
						confession['id']
					)
				except discord.HTTPException as e:
					logger.error(
						"Failed to fetch or edit moderation message for Confession #%s: %s",
						confession['id'],
						e
					)

	def cog_unload(self):
		"""Cleanup when the cog is unloaded."""
		logger.info("Unloading ConfessionCog...")

		# Stop the hourly posting task
		self.service.stop_posting()

		logger.info("ConfessionCog unloaded successfully")
