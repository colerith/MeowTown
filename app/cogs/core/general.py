import discord
from discord.ext import commands

from app.cogs.gameplay.cat import TOWN_GROUP
from app.shared.helpers import get_help_embed


class General(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@TOWN_GROUP.command(name="帮助", description="查看喵喵小镇完全指南")
	async def help(self, ctx: discord.ApplicationContext):
		avatar_url = self.bot.user.display_avatar.url if self.bot.user else None
		embed = get_help_embed(avatar_url)
		await ctx.respond(embed=embed, ephemeral=True)

	@TOWN_GROUP.command(name="延迟", description="查看机器人的网络延迟")
	async def ping(self, ctx: discord.ApplicationContext):
		latency = round(self.bot.latency * 1000)
		await ctx.respond(f"🏓 Pong! 延迟: **{latency}ms**", ephemeral=True)


def setup(bot):
	bot.add_cog(General(bot))
