import discord
from discord.ext import commands
from discord.ui import Button, Select, View

from app.db.repositories.title_repo import (
    check_title_owned,
    equip_user_title,
    get_user_titles,
    unlock_title,
)
from app.db.repositories.user_repo import get_citizen, update_money
from app.shared.data.title_data import RARITY_CONFIG, TITLES, TITLE_DRAW_COST, draw_random_title

TITLE_IMAGE = "https://i.postimg.cc/4dFbg1Qj/title.png"


async def build_title_panel_embed(user_id):
    owned_ids = await get_user_titles(user_id)
    user = await get_citizen(user_id)
    active_title = user[6] if user and len(user) > 6 and user[6] else None

    embed = discord.Embed(title="🏷️ 喵喵称号中心", color=discord.Color.gold())
    embed.set_image(url=TITLE_IMAGE)

    if not owned_ids:
        embed.description = f"你还没有称号。\n点击下方 `抽一发`，花费 **{TITLE_DRAW_COST}** 喵币试试手气。"
        return embed

    sorted_ids = sorted(
        owned_ids,
        key=lambda x: ["SSR", "SR", "R", "N"].index(TITLES.get(x, {}).get("rarity", "N")),
    )
    lines = []
    for tid in sorted_ids:
        data = TITLES.get(tid)
        if not data:
            continue
        rarity_name = RARITY_CONFIG[data["rarity"]]["name"]
        line = f"**【{data['name']}】** ({rarity_name})"
        if active_title == data["name"]:
            line += " ✅"
        lines.append(line)

    embed.description = "\n".join(lines)
    embed.set_footer(text=f"当前共有 {len(lines)} 个称号 | 抽取花费 {TITLE_DRAW_COST} 喵币")
    return embed


class TitleEquipSelect(Select):
    def __init__(self, user_id, owned_ids):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=TITLES[tid]["name"],
                description=f"稀有度 {RARITY_CONFIG[TITLES[tid]['rarity']]['name']}",
                value=TITLES[tid]["name"],
            )
            for tid in owned_ids
            if tid in TITLES
        ]
        super().__init__(placeholder="选择要佩戴的称号...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的称号面板。", ephemeral=True)

        title_name = self.values[0]
        await equip_user_title(self.user_id, title_name)
        await interaction.response.send_message(f"✅ 你现在佩戴的是 **【{title_name}】**。", ephemeral=True)


class TitlePanelView(View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="抽一发", style=discord.ButtonStyle.success, emoji="🎰", row=0)
    async def draw_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的称号面板。", ephemeral=True)

        user = await get_citizen(self.user_id)
        if user[4] < TITLE_DRAW_COST:
            return await interaction.response.send_message(
                f"🚫 你的喵币不足！抽一次需要 **{TITLE_DRAW_COST}** 喵币。",
                ephemeral=True,
            )

        await update_money(self.user_id, -TITLE_DRAW_COST)
        tid, title_data = draw_random_title()
        rarity_info = RARITY_CONFIG[title_data["rarity"]]
        is_owned = await check_title_owned(self.user_id, tid)

        embed = discord.Embed(title="🎰 称号扭蛋机", color=rarity_info["color"])
        embed.set_image(url=TITLE_IMAGE)

        if is_owned:
            refund = int(TITLE_DRAW_COST / 2)
            await update_money(self.user_id, refund)
            embed.description = (
                f"你抽到了：**【{title_data['name']}】** ({rarity_info['name']})\n\n"
                f"😕 已经拥有该称号，系统退还 **{refund}** 喵币。"
            )
        else:
            await unlock_title(self.user_id, tid)
            embed.description = (
                f"🎉 **恭喜！你获得了一个新称号！**\n\n"
                f"🏷️ **【{title_data['name']}】**\n"
                f"✨ 稀有度：**{rarity_info['name']}**"
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="佩戴称号", style=discord.ButtonStyle.primary, emoji="👑", row=0)
    async def equip_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的称号面板。", ephemeral=True)

        owned_ids = await get_user_titles(self.user_id)
        if not owned_ids:
            return await interaction.response.send_message("你还没有称号可佩戴。", ephemeral=True)

        view = View(timeout=120)
        view.add_item(TitleEquipSelect(self.user_id, owned_ids))
        await interaction.response.send_message("请选择一个称号进行佩戴：", view=view, ephemeral=True)

    @discord.ui.button(label="刷新列表", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def refresh_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的称号面板。", ephemeral=True)

        embed = await build_title_panel_embed(self.user_id)
        await interaction.response.edit_message(embed=embed, view=self)


async def open_title_panel(interaction: discord.Interaction, user_id: int):
    embed = await build_title_panel_embed(user_id)
    await interaction.response.send_message(embed=embed, view=TitlePanelView(user_id), ephemeral=True)


class Title(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Title(bot))
