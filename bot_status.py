import discord
from discord.ext import commands
import traceback

class BotStatus(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		try:
			activity = discord.Activity(type=discord.ActivityType.listening, name='my hair 💁🏻‍♀️')
			await self.bot.change_presence(activity=activity)
		except Exception as e:
			print(f'Error! {e}')
# Setup the Cog
async def setup(bot):
	await bot.add_cog(BotStatus(bot))