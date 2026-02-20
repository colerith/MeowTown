# modules/profile/ui.py
import discord
from discord import ui
from typing import List

# 从同模块导入依赖
from . import database
from . import data as profile_data

# --- 更换称号的 Modal ---
class TitleSelectModal(ui.Modal, title="更换称号"):
    def __init__(self, db_pool: discord.Bot, owned_title_ids: List[str]):
        super().__init__()
        self.db_pool = db_pool

        options = [discord.SelectOption(label="卸下称号", value="无名之辈", emoji="🚫")]
        for tid in owned_title_ids:
            title = profile_data.TITLES.get(tid)
            if title:
                rarity = profile_data.RARITY_CONFIG[title['rarity']]['name']
                options.append(discord.SelectOption(
                    label=title['name'],
                    value=title['name'],
                    description=f"稀有度: {rarity}"
                ))

        self.title_select = ui.Label(
            text="选择一个你要佩戴的新称号:",
            component=ui.Select(
                custom_id="title_select",
                placeholder="请选择你的称号...",
                options=options
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        new_title_name = self.title_select.component.values[0]
        await database.equip_title(self.db_pool, interaction.user.id, new_title_name)
        await interaction.response.send_message(f"✅ 称号已更换为 **【{new_title_name}】**！", ephemeral=True)


# --- 核心档案 Container 视图 ---
class ProfileContainerView(ui.LayoutView):
    def __init__(self, bot: discord.Bot, db_pool: discord.Bot, author: discord.User, citizen_data: tuple):
        super().__init__(timeout=180)
        self.bot = bot
        self.db_pool = db_pool
        self.author = author
        self.citizen_data = citizen_data

        # --- 定义组件 ---
        self.btn_change_title = ui.Button(label="更换称号", style=discord.ButtonStyle.primary, emoji="🏷️")
        self.btn_change_title.callback = self.change_title_callback

        self.btn_inventory = ui.Button(label="我的背包", style=discord.ButtonStyle.green, emoji="🎒")
        self.btn_inventory.callback = self.inventory_callback

        self.btn_quick_shop = ui.Button(label="快捷商店", style=discord.ButtonStyle.secondary, emoji="🛍️")
        # self.btn_quick_shop.callback = self.shop_callback # 商店功能后续实现

        # --- 主容器 ---
        name, species, pattern, money, _, active_title, *_ = self.citizen_data

        container = ui.Container(
            # 顶栏：头像和名字
            ui.Section(
                ui.TextDisplay(content=f"### {name}"),
                ui.TextDisplay(content=f"**头衔:** 【{active_title or '无名之辈'}】"),
                accessory=ui.Thumbnail(media=author.display_avatar.url),
            ),
            ui.Separator(),
            # 中间：详细信息
            ui.TextDisplay(content=f"**🧬 品种:** {species}"),
            ui.TextDisplay(content=f"**🎨 花色:** {pattern}"),
            ui.TextDisplay(content=f"**💰 资产:** {money:.2f} 喵币"),
            ui.Separator(spacing=discord.SeparatorSpacing.large),
            # 底部：交互按钮
            ui.ActionRow(
                self.btn_change_title,
                self.btn_inventory,
                self.btn_quick_shop
            ),
            accent_colour=discord.Color.gold()
        )
        self.add_item(container)

    async def change_title_callback(self, interaction: discord.Interaction):
        # 仅限本人操作
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)

        owned_ids = await database.get_user_titles(self.db_pool, self.author.id)
        if not owned_ids:
            return await interaction.response.send_message("你还没有任何称号，快去抽奖吧！", ephemeral=True)

        modal = TitleSelectModal(self.db_pool, owned_ids)
        await interaction.response.send_modal(modal)

    async def inventory_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        # 背包功能后续实现
        await interaction.response.send_message("背包功能正在施工中...", ephemeral=True)