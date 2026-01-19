"""
Gretchen - Discord Confession Bot

A Discord bot that handles anonymous confessions for The Cult of Sir.
Confessions are submitted anonymously, moderated, and posted on a schedule.
"""
import logging
import asyncio
import traceback

import discord
from discord.ext import commands
import setproctitle

from config import LOG_FILE, LOG_LEVEL, BOT_TOKEN

# Set process title for system monitoring
setproctitle.setproctitle('gretchen')

# Configure logging
logging.basicConfig(
	level=LOG_LEVEL,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
	handlers=[
		logging.FileHandler(LOG_FILE),
	]
)
logger = logging.getLogger("GretchenBot")

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
	"""Handle bot ready event and sync application commands."""
	logger.info("Bot is ready")
	try:
		await bot.tree.sync()
		logger.info("Application commands synced successfully")
	except Exception as e:
		logger.error("Failed to sync commands: %s", e)


@bot.event
async def on_error(event_method):
	"""
	Handle errors in event methods.

	Args:
		event_method: The name of the event that raised an error
		*args: Positional arguments passed to the event
		**kwargs: Keyword arguments passed to the event
	"""
	logger.error("Error in %s:", event_method)
	traceback.print_exc()


async def run_bot():
	"""Load extensions and start the bot."""
	try:
		await bot.load_extension('cogs.confession')
		await bot.load_extension('bot_status')
		logger.info("Extensions loaded successfully")
		await bot.start(BOT_TOKEN)
	except Exception as e:
		logger.error("Failed to start bot: %s", e, exc_info=True)


if __name__ == "__main__":
	logger.info("Starting Gretchen bot...")
	asyncio.run(run_bot())
