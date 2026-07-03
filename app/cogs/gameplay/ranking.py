# cogs/ranking.py
import discord
from discord.ext import commands
from discord.ui import View, Select
from app.db.repositories.ranking_repo import (
    get_top_bank_users,
    get_top_casino_winners,
    get_top_farm_steal_users,
    get_top_jail_users,
    get_top_money_users,
    get_top_property_owners,
    get_top_robbery_users,
)
from app.features.economy.service import format_economy_amount

IMG_RANK = "https://i.postimg.cc/RCyR2z9z/ranking.png"


def build_medal(index: int):
    return ["🥇", "🥈", "🥉"][index] if index < 3 else f"`{index + 1}.`"


def format_amount(value):
    return format_economy_amount(value)


def format_rank_user(user_id, cat_name):
    return f"<@{user_id}> / {cat_name}"

class RankSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="富豪排行榜", value="money", description="按持有现金排名", emoji="💰"),
            discord.SelectOption(label="地主排行榜", value="land", description="按大富翁房产数量排名", emoji="🏰"),
            discord.SelectOption(label="娱乐场排行榜", value="casino", description="按娱乐城获胜场次排名", emoji="🎰"),
            discord.SelectOption(label="入狱排行榜", value="jail", description="按累计入狱次数排名", emoji="🚓"),
            discord.SelectOption(label="银行排行榜", value="bank", description="按银行总存款排名", emoji="🏦"),
            discord.SelectOption(label="打劫排行榜", value="robbery", description="按犯罪得手次数排名", emoji="🔫"),
            discord.SelectOption(label="偷菜排行榜", value="steal", description="按农场偷菜成功次数排名", emoji="🥬"),
        ]
        super().__init__(placeholder="选择排行榜类型...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        rank_type = self.values[0]
        embed = await self.generate_rank_embed(rank_type)
        await interaction.response.edit_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    async def generate_rank_embed(self, rank_type):
        embed = discord.Embed(title="🏆 喵喵小镇风云榜", color=0xFFD700)
        embed.set_image(url=IMG_RANK)
        
        if rank_type == "money":
            rows = await get_top_money_users()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                desc += f"{medal} {format_rank_user(row[0], row[1])} - {format_amount(row[2])} 喵币\n"
            embed.add_field(name="💰 十大富豪", value=desc if desc else "大家的钱包都还在发育中。")
             
        elif rank_type == "land":
            rows = await get_top_property_owners()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                desc += f"{medal} {format_rank_user(row[0], row[1])} - {row[2]} 处房产\n"
            embed.add_field(name="🏰 十大地主", value=desc if desc else "地皮都还没炒热，先别急着当包租喵。")

        elif rank_type == "casino":
            rows = await get_top_casino_winners()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                desc += f"{medal} {format_rank_user(row[0], row[1])} - {row[2]} 胜 / {row[3]} 负\n"
            embed.add_field(name="🎰 娱乐场高手榜", value=desc if desc else "赌神们今天都在摸鱼，筹码台空空如也。")

        elif rank_type == "jail":
            rows = await get_top_jail_users()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                desc += f"{medal} {format_rank_user(row[0], row[1])} - 入狱 {row[2]} 次\n"
            embed.add_field(name="🚓 铁窗常客榜", value=desc if desc else "本镇治安良好，暂时没人常住铁窗单间。")

        elif rank_type == "bank":
            rows = await get_top_bank_users()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                desc += (
                    f"{medal} {format_rank_user(row[0], row[1])} - 总存款 {format_amount(row[2])}\n"
                    f"活期 {format_amount(row[3])} / 定期 {format_amount(row[4])}\n"
                )
            embed.add_field(name="🏦 银行储蓄榜", value=desc if desc else "存款柜台今天很安静，大家的钱可能都出去浪了。")

        elif rank_type == "robbery":
            rows = await get_top_robbery_users()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                total_success = int(row[2]) + int(row[3])
                desc += (
                    f"{medal} {format_rank_user(row[0], row[1])} - 得手 {total_success} 次\n"
                    f"路抢 {row[2]} / 银抢 {row[3]} / 卷走 {format_amount(row[4])} 喵币\n"
                )
            embed.add_field(name="🔫 黑市悍匪榜", value=desc if desc else "大家今天都挺守法，黑吃黑榜单还没开张。")

        elif rank_type == "steal":
            rows = await get_top_farm_steal_users()
            desc = ""
            for i, row in enumerate(rows):
                medal = build_medal(i)
                desc += (
                    f"{medal} {format_rank_user(row[0], row[1])} - 偷成 {row[2]} 次\n"
                    f"翻车 {row[3]} 次 / 销赃 {format_amount(row[4])} 喵币\n"
                )
            embed.add_field(name="🥬 菜园怪盗榜", value=desc if desc else "菜园子风平浪静，暂时没人半夜进地偷菜。")

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
