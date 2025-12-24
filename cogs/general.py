# cogs/general.py
import discord
from discord.ext import commands
from utils.helpers import get_help_embed

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="帮助", description="查看喵喵小镇完全指南")
    async def help(self, ctx: discord.ApplicationContext):
        # 获取机器人头像，如果没有则由None处理(discord会自动处理空url吗? 最好给个默认图或者取bot.user.avatar)
        avatar_url = self.bot.user.display_avatar.url if self.bot.user else None
        
        embed = get_help_embed(avatar_url)
        # ephemeral=True 让消息只有发送者能看到，防止刷屏
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="延迟", description="查看机器人的网络延迟")
    async def ping(self, ctx: discord.ApplicationContext):
        latency = round(self.bot.latency * 1000)
        await ctx.respond(f"🏓 Pong! 延迟: **{latency}ms**", ephemeral=True)

def setup(bot):
    bot.add_cog(General(bot))
