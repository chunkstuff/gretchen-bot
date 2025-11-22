"""
Confession cog package - Anonymous confession submission and posting system.
"""
from .cog import ConfessionCog

async def setup(bot):
	"""Setup function for loading the confession cog."""
	await bot.add_cog(ConfessionCog(bot))