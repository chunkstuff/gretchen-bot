import discord
from discord.ext import commands
import traceback

class BotStatus(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_ready(self):
		try:
			await self.bot.change_presence(
				activity=discord.CustomActivity(
					name="💁‍♀️ It's full of secrets 😏"
				)
			)
		except Exception as e:
			print(f'Error! {e}')
# Setup the Cog
async def setup(bot):
	await bot.add_cog(BotStatus(bot))