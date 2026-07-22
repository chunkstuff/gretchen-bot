"""
Discord UI components for confessions (modals, buttons, views).
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord.ui import View, Button, Modal, TextInput

from .embeds import (
	create_approval_embed,
	create_rejection_embed,
	create_submission_embed
)
from .services import next_post_time

logger = logging.getLogger(__name__)


class ConfessionModal(Modal):
	"""Modal for submitting a confession."""

	def __init__(self, cog):
		"""
		Initialize the confession modal.

		Args:
			cog: The ConfessionCog instance
		"""
		super().__init__(title="You let it out, honey!")
		self.cog = cog
		self.add_item(
			TextInput(
				label="Put it in the book...",
				placeholder="Enter your confession here...",
				custom_id="confession_text",
				style=discord.TextStyle.long,
			)
		)

	async def on_submit(self, interaction: discord.Interaction):
		"""
		Handle confession submission.

		Args:
			interaction: The Discord interaction from the modal submission
		"""
		try:
			full_text = self.children[0].value

			# Create a confession with default "submitted" status
			confession = {
				"id": self.cog.data.confession_counter,
				"user_id": str(interaction.user.id),
				"username": interaction.user.display_name,
				"text": full_text,
				"status": "submitted",
				"submission_time": datetime.utcnow().isoformat(),
				"message_id": None,
			}

			# Add the confession to the submission queue
			self.cog.data.add_submission(confession)
			logger.info(
				"Confession #%s added to submission queue by %s",
				confession['id'],
				interaction.user.display_name
			)

			# Send a notification to the moderation channel
			mod_channel = self.cog.bot.get_channel(
				self.cog.moderator_channel_id
			)
			if mod_channel:
				embed = create_submission_embed(confession)
				view = ConfessionNotificationView(self.cog, confession)
				mod_message = await mod_channel.send(embed=embed, view=view)

				confession["message_id"] = mod_message.id
				self.cog.data.save()
				logger.info(
					"Confession #%s sent to moderation channel with message ID %s",
					confession['id'],
					mod_message.id
				)

			# Acknowledge submission to the user
			await interaction.response.send_message(
				"Don't worry, honey, your secret is safe with me! ✨👀",
				ephemeral=True
			)
			logger.info(
				"User %s successfully submitted confession #%s",
				interaction.user.display_name,
				confession['id']
			)

		except Exception as e:
			logger.error("Error during confession submission: %s", e, exc_info=True)
			await interaction.response.send_message(
				"Oops! Something went wrong. Please try again later. 💔",
				ephemeral=True
			)


class ConfessionNotificationView(View):
	"""View for moderator actions on submitted confessions."""

	def __init__(self, cog, confession):
		"""
		Initialize the moderation view.

		Args:
			cog: The ConfessionCog instance
			confession: The confession dict being moderated
		"""
		super().__init__(timeout=None)
		self.cog = cog
		self.confession = confession

	@discord.ui.button(label="Approve ✅", style=discord.ButtonStyle.success)
	async def approve_button(self, interaction: discord.Interaction, button: Button):
		"""
		Handle confession approval.

		Args:
			interaction: The Discord interaction from button click
			button: The button that was clicked
		"""
		confession = self.confession
		self.cog.data.remove_submission(confession)
		confession["status"] = "approved"

		# Add to post queue
		self.cog.data.add_to_post_queue(confession)

		# Calculate when this will actually post based on queue position
		queue_position = len(self.cog.data.post_queue)  # Position in queue (1-indexed)

		# Position 1 posts at the next :15, position 2 the hour after, etc.
		next_run = next_post_time(datetime.now(timezone.utc))
		next_run += timedelta(hours=queue_position - 1)

		# Convert to UK time for display
		uk_tz = ZoneInfo("Europe/London")
		next_run_uk = next_run.astimezone(uk_tz)
		posting_time = next_run_uk.strftime("%d %b at %H:%M UK")

		# Update the original embed
		embed = interaction.message.embeds[0]
		embed.color = discord.Color.green()
		embed.title = f"Confession #{confession['id']} (Approved)"
		await interaction.message.edit(embed=embed, view=None)

		# Send approval notification embed
		approval_embed = create_approval_embed(
			confession,
			interaction.user,
			posting_time,
			queue_position
		)
		await interaction.response.send_message(embed=approval_embed)

	@discord.ui.button(label="Reject ❌", style=discord.ButtonStyle.danger)
	async def reject_button(self, interaction: discord.Interaction, button: Button):
		"""
		Handle confession rejection.

		Args:
			interaction: The Discord interaction from button click
			button: The button that was clicked
		"""
		confession = self.confession
		self.cog.data.remove_submission(confession)
		confession["status"] = "rejected"

		# Archive rejected confession
		self.cog.data.archive(confession)

		# Update the original embed
		embed = interaction.message.embeds[0]
		embed.color = discord.Color.red()
		embed.title = f"Confession #{confession['id']} (Rejected)"
		await interaction.message.edit(embed=embed, view=None)

		# Send rejection notification embed
		rejection_embed = create_rejection_embed(confession, interaction.user)
		await interaction.response.send_message(embed=rejection_embed)


class PersistentView(View):
	"""Persistent view with the main confession button."""

	def __init__(self, cog):
		"""
		Initialize the persistent view.

		Args:
			cog: The ConfessionCog instance
		"""
		super().__init__(timeout=None)
		self.add_item(ConfessionButton(cog))


class ConfessionButton(Button):
	"""Main button for submitting confessions."""

	def __init__(self, cog):
		"""
		Initialize the confession button.

		Args:
			cog: The ConfessionCog instance
		"""
		super().__init__(
			label="🤭 Add to my hair!",
			style=discord.ButtonStyle.danger
		)
		self.cog = cog

	async def callback(self, interaction: discord.Interaction):
		"""
		Handle button click to open confession modal.

		Args:
			interaction: The Discord interaction from button click
		"""
		await interaction.response.send_modal(ConfessionModal(self.cog))
