# cogs/ranking.py
import discord
from discord.ext import commands
from discord.ui import View, Select
from app.db.repositories.ranking_repo import get_top_money_users, get_top_property_owners

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
        
        if rank_type == "money":
            rows = await get_top_money_users()
            desc = ""
            for i, row in enumerate(rows):
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`{i+1}.`"
                desc += f"{medal} **{row[0]}** - {row[1]:.2f} 喵币\n"
            embed.add_field(name="💰 十大富豪", value=desc if desc else "暂无数据")
            
        elif rank_type == "land":
            rows = await get_top_property_owners()
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

async def create_ranking_dashboard():
    view = RankingView()
    embed = await view.children[0].generate_rank_embed("money")
    return embed, view

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Ranking(bot))
