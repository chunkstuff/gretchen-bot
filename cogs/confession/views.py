"""
Discord UI components for confessions (modals, buttons, views).
"""
import logging
from datetime import datetime

import discord
from discord.ui import View, Button, Modal, TextInput

logger = logging.getLogger(__name__)


class ConfessionModal(Modal):
	"""Modal for submitting a confession."""
	
	def __init__(self, cog):
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
		try:
			full_text = self.children[0].value
			truncated_text = (full_text[:147] + '...') if len(full_text) > 150 else full_text

			# Create a confession with default "submitted" status
			confession = {
				"id": self.cog.data.confession_counter,
				"user_id": str(interaction.user.id),
				"username": interaction.user.display_name,
				"text": full_text,
				"status": "submitted",
				"submission_time": datetime.utcnow().isoformat(),
				"message_id": None,
				"scheduled_time": None,  # This will be set upon approval
			}

			# Add the confession to the submission queue
			self.cog.data.add_submission(confession)
			logger.info(f"Confession #{confession['id']} added to submission queue by {interaction.user.display_name}")

			# Send a notification to the moderation channel
			mod_channel = self.cog.bot.get_channel(self.cog.moderator_channel_id)
			if mod_channel:
				embed = discord.Embed(
					title=f"New Confession Submitted (#{confession['id']})",
					description=truncated_text,
					color=discord.Color.yellow(),
				)
				mod_message = await mod_channel.send(embed=embed, view=ConfessionNotificationView(self.cog, confession))
				confession["message_id"] = mod_message.id
				self.cog.data.save()
				logger.info(f"Confession #{confession['id']} sent to moderation channel with message ID {mod_message.id}")

			# Acknowledge submission to the user
			await interaction.response.send_message("Don't worry, honey, your secret is safe with me! ✨👀", ephemeral=True)
			logger.info(f"User {interaction.user.display_name} successfully submitted confession #{confession['id']}")
		except Exception as e:
			logger.error(f"Error during confession submission: {e}", exc_info=True)
			await interaction.response.send_message("Oops! Something went wrong. Please try again later. 💔", ephemeral=True)


class ConfessionNotificationView(View):
	"""View for moderator actions on submitted confessions."""
	
	def __init__(self, cog, confession):
		super().__init__(timeout=None)
		self.cog = cog
		self.confession = confession
		self.show_full_message = False

	@discord.ui.button(label="Approve ✅", style=discord.ButtonStyle.success)
	async def approve_button(self, interaction: discord.Interaction, button: Button):
		confession = self.confession
		self.cog.data.remove_submission(confession)
		confession["status"] = "approved"

		# Schedule for the next available 2am UK time
		next_2am = self.cog.service.get_next_2am_uk()
		confession["scheduled_time"] = next_2am.isoformat()

		self.cog.data.add_to_post_queue(confession)
		
		# Schedule the confession to be posted at the designated time
		self.cog.service.schedule_confession_post(confession)

		# Format the time nicely for display
		scheduled_time_str = next_2am.strftime("%Y-%m-%d at 2:00 AM UK time")

		embed = interaction.message.embeds[0]
		embed.color = discord.Color.green()
		embed.title = f"Confession #{confession['id']} (Approved)"
		embed.set_footer(
			text=f"Submitted by: {confession['username']} | Submitted on: {confession['submission_time']}"
		)
		await interaction.message.edit(embed=embed, view=None)
		await interaction.response.send_message(
			f"Confession #{confession['id']} approved and scheduled for {scheduled_time_str}.", 
			ephemeral=True
		)

	@discord.ui.button(label="Reject ❌", style=discord.ButtonStyle.danger)
	async def reject_button(self, interaction: discord.Interaction, button: Button):
		confession = self.confession
		self.cog.data.remove_submission(confession)
		confession["status"] = "rejected"
		
		# Archive rejected confession
		self.cog.data.archive(confession)

		embed = interaction.message.embeds[0]
		embed.color = discord.Color.red()
		embed.title = f"Confession #{confession['id']} (Rejected)"
		embed.set_footer(
			text=f"Submitted by: {confession['username']} | Submitted on: {confession['submission_time']}"
		)
		await interaction.message.edit(embed=embed, view=None)
		await interaction.response.send_message(
			f"Confession #{confession['id']} rejected.",
			ephemeral=True
		)

	@discord.ui.button(label="Toggle Message 📝", style=discord.ButtonStyle.secondary)
	async def toggle_message_button(self, interaction: discord.Interaction, button: Button):
		self.show_full_message = not self.show_full_message
		embed = interaction.message.embeds[0]

		if self.show_full_message:
			embed.description = f"**Full Message:**\n```\n{self.confession['text']}\n```"
			button.label = "Show Shortened Message 📝"
		else:
			truncated_text = self.confession["text"][:147] + "..." if len(self.confession["text"]) > 150 else self.confession["text"]
			embed.description = f"**Truncated Message:**\n\n{truncated_text}\n"
			button.label = "Show Full Message 📝"

		embed.set_footer(
			text=f"Submitted by: {self.confession['username']} | Submitted on: {self.confession['submission_time']}"
		)
		await interaction.message.edit(embed=embed, view=self)
		await interaction.response.send_message("Message toggled.", ephemeral=True)


class PersistentView(View):
	"""Persistent view with the main confession button."""
	
	def __init__(self, cog):
		super().__init__(timeout=None)
		self.add_item(ConfessionButton(cog))


class ConfessionButton(Button):
	"""Main button for submitting confessions."""
	
	def __init__(self, cog):
		super().__init__(label="🤭 Add to my hair!", style=discord.ButtonStyle.danger)
		self.cog = cog

	async def callback(self, interaction: discord.Interaction):
		await self.cog.open_modal(interaction)