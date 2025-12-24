# cogs/ranking.py
import discord
import aiosqlite
from discord.ext import commands
from discord.ui import View, Select
from utils.db import DB_PATH

IMG_RANK = "https://i.postimg.cc/RCyR2z9z/ranking.png"

class RankSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="富豪排行榜", value="money", description="按持有现金排名", emoji="💰"),
            discord.SelectOption(label="地主排行榜", value="land", description="按大富翁房产数量排名", emoji="🏰"),
        ]
        super().__init__(placeholder="选择排行榜类型...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        rank_type = self.values[0]
        embed = await self.generate_rank_embed(rank_type)
        await interaction.response.edit_message(embed=embed)

    async def generate_rank_embed(self, rank_type):
        embed = discord.Embed(title="🏆 喵喵小镇风云榜", color=0xFFD700)
        embed.set_image(url=IMG_RANK)
        
        async with aiosqlite.connect(DB_PATH) as db:
            if rank_type == "money":
                cursor = await db.execute("SELECT cat_name, money FROM users ORDER BY money DESC LIMIT 10")
                rows = await cursor.fetchall()
                desc = ""
                for i, row in enumerate(rows):
                    medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`{i+1}.`"
                    # 修改处：使用 :.2f 保留两位小数
                    desc += f"{medal} **{row[0]}** - {row[1]:.2f} 喵币\n"
                embed.add_field(name="💰 十大富豪", value=desc if desc else "暂无数据")
                
            elif rank_type == "land":
                # 联表查询：统计 monopoly_properties 中 owner_id 出现的次数
                sql = """
                    SELECT u.cat_name, COUNT(p.map_id) as count 
                    FROM monopoly_properties p 
                    JOIN users u ON p.owner_id = u.user_id 
                    GROUP BY p.owner_id 
                    ORDER BY count DESC 
                    LIMIT 10
                """
                cursor = await db.execute(sql)
                rows = await cursor.fetchall()
                desc = ""
                for i, row in enumerate(rows):
                    medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`{i+1}.`"
                    desc += f"{medal} **{row[0]}** - {row[1]} 处房产\n"
                embed.add_field(name="🏰 十大地主", value=desc if desc else "暂无数据")

        return embed

class RankingView(View):
    def __init__(self):
        super().__init__()
        self.add_item(RankSelect())

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="排行榜", description="查看小镇名人堂")
    async def leaderboard(self, ctx: discord.ApplicationContext):
        # 默认显示富豪榜
        view = RankingView()
        # 手动调用一次生成逻辑获取初始 Embed
        embed = await view.children[0].generate_rank_embed("money")
        await ctx.respond(embed=embed, view=view)

def setup(bot):
    bot.add_cog(Ranking(bot))