# modules/profile/cog.py
import discord
from discord.ext import commands

from . import ui, database
from . import data as profile_data

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db_pool):
        self.bot = bot
        self.db_pool = db_pool

    profile = discord.SlashCommandGroup("profile", "喵喵小镇市民档案系统")

    @profile.command(name="register", description="登记身份，入住喵喵小镇！")
    async def register(self, ctx: discord.ApplicationContext, name: discord.Option(str, "给你的喵喵起个名字")):
        if await database.get_citizen(self.db_pool, ctx.author.id):
            return await ctx.respond("🚫 你已经是小镇居民了！", ephemeral=True)

        species, pattern, money, is_special = profile_data.generate_cat_identity()
        await database.create_citizen(self.db_pool, ctx.author.id, name, species, pattern, money)

        embed = discord.Embed(title="🎉 欢迎入住喵喵小镇！", description=f"市民登记完成，欢迎 **{name}** 加入大家庭。", color=0x00FF00)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🧬 品种", value=species, inline=True)
        embed.add_field(name="🎨 花色", value=pattern, inline=True)

        if is_special:
            embed.add_field(name="✨ 天赋异禀", value=f"触发隐藏款组合！获得启动金 **{money:.2f} 喵币**！", inline=False)
        else:
            embed.add_field(name="💰 初始资金", value=f"{money:.2f} 喵币", inline=False)

        await ctx.respond(embed=embed)

    @profile.command(name="view", description="查看我的或他人的市民档案")
    async def view(self, ctx: discord.ApplicationContext, user: discord.Option(discord.Member, "选择要查看的市民", required=False)):
        target_user = user or ctx.author

        citizen_data = await database.get_citizen(self.db_pool, target_user.id)
        if not citizen_data:
            return await ctx.respond(f"🚫 **{target_user.display_name}** 还不是小镇居民！", ephemeral=True)

        # 传入所需参数，创建并发送视图
        view = ui.ProfileContainerView(self.bot, self.db_pool, target_user, citizen_data)
        await ctx.respond(view=view)

    @commands.slash_command(name="title_draw", description=f"花费 {profile_data.TITLE_DRAW_COST} 喵币抽取一个称号")
    async def title_draw(self, ctx: discord.ApplicationContext):
        citizen = await database.get_citizen(self.db_pool, ctx.author.id)
        if not citizen:
            return await ctx.respond("🚫 你还不是小镇居民！请先注册。", ephemeral=True)

        if citizen[4] < profile_data.TITLE_DRAW_COST:
            return await ctx.respond(f"🚫 余额不足！需要 **{profile_data.TITLE_DRAW_COST}** 喵币。", ephemeral=True)

        await database.update_money(self.db_pool, ctx.author.id, -profile_data.TITLE_DRAW_COST)

        tid, title_data = profile_data.draw_random_title()
        rarity_info = profile_data.RARITY_CONFIG[title_data['rarity']]

        is_owned = await database.check_title_owned(self.db_pool, ctx.author.id, tid)

        embed = discord.Embed(title="🎰 称号扭蛋机", color=rarity_info['color'])
        if is_owned:
            refund = int(profile_data.TITLE_DRAW_COST / 2)
            await database.update_money(self.db_pool, ctx.author.id, refund)
            embed.description = f"你抽到了：**【{title_data['name']}】**\n\n😕 可惜你已经有了！系统退还 **{refund}** 喵币。"
        else:
            await database.unlock_title(self.db_pool, ctx.author.id, tid)
            embed.description = f"🎉 **恭喜！获得新称号！**\n\n🏷️ **【{title_data['name']}】**\n✨ 稀有度：**{rarity_info['name']}**"

        await ctx.respond(embed=embed)