import os
import logging
import discord
import asyncio
import traceback
from discord.ext import commands
import setproctitle

from config import LOG_FILE, LOG_LEVEL, BOT_TOKEN

setproctitle.setproctitle('gretchen')

# Set up logger
logging.basicConfig(
	level=LOG_LEVEL,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
	handlers=[
		logging.FileHandler(LOG_FILE),
	]
)
logger = logging.getLogger("GretchenBot")


# Bot token and intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True	# For slash commands and guild interactions

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
	print("Bot is ready")
	try:
		await bot.tree.sync()
		print("Application commands synced successfully")
	except Exception as e:
		print(f"Failed to sync commands: {e}")

@bot.event
async def on_error(event_method, *args, **kwargs):
	print(f"Error in {event_method}:")
	traceback.print_exc()

async def run_bot():
	await bot.load_extension('cogs.confession')
	await bot.load_extension('bot_status')
	await bot.start(BOT_TOKEN)

print(BOT_TOKEN)
asyncio.run(run_bot())