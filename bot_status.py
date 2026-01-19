"""
Bot Status Cog

Sets Gretchen's custom status/presence when the bot comes online.
"""
import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class BotStatus(commands.Cog):
	"""Cog for managing bot presence and status."""

	def __init__(self, bot):
		"""
		Initialize the BotStatus cog.
		
		Args:
			bot: The Discord bot instance
		"""
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		"""Set bot's custom status when ready."""
		try:
			await self.bot.change_presence(
				activity=discord.CustomActivity(
					name="💁‍♀️ It's full of secrets 😏"
				)
			)
			logger.info("Bot status set successfully")
		except Exception as e:
			logger.error("Failed to set bot status: %s", e)


async def setup(bot):
	"""
	Setup function for loading the bot status cog.
	
	Args:
		bot: The Discord bot instance
	"""
	await bot.add_cog(BotStatus(bot))
