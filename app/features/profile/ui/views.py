import discord
from discord import ui

from app.features.profile import repository
from app.features.profile.ui.modals import TitleSelectModal


class ProfileContainerView(ui.LayoutView):
	def __init__(self, bot: discord.Bot, db_pool: discord.Bot, author: discord.User, citizen_data: tuple):
		super().__init__(timeout=180)
		self.bot = bot
		self.db_pool = db_pool
		self.author = author
		self.citizen_data = citizen_data

		self.btn_change_title = ui.Button(label="更换称号", style=discord.ButtonStyle.primary, emoji="🏷️")
		self.btn_change_title.callback = self.change_title_callback

		self.btn_inventory = ui.Button(label="我的背包", style=discord.ButtonStyle.green, emoji="🎒")
		self.btn_inventory.callback = self.inventory_callback

		self.btn_quick_shop = ui.Button(label="主商店", style=discord.ButtonStyle.secondary, emoji="🛍️")

		name, species, pattern, money, _, active_title, *_ = self.citizen_data

		container = ui.Container(
			ui.Section(
				ui.TextDisplay(content=f"### {name}"),
				ui.TextDisplay(content=f"**头衔:** 【{active_title or '无名之辈'}】"),
				accessory=ui.Thumbnail(media=author.display_avatar.url),
			),
			ui.Separator(),
			ui.TextDisplay(content=f"**🧬 品种:** {species}"),
			ui.TextDisplay(content=f"**🎨 花色:** {pattern}"),
			ui.TextDisplay(content=f"**💰 资产:** {money:.2f} 喵币"),
			ui.Separator(spacing=discord.SeparatorSpacing.large),
			ui.ActionRow(self.btn_change_title, self.btn_inventory, self.btn_quick_shop),
			accent_colour=discord.Color.gold(),
		)
		self.add_item(container)

	async def change_title_callback(self, interaction: discord.Interaction):
		if interaction.user.id != self.author.id:
			return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)

		owned_ids = await repository.get_user_titles(self.db_pool, self.author.id)
		if not owned_ids:
			return await interaction.response.send_message("你还没有任何称号，快去抽奖吧！", ephemeral=True)

		modal = TitleSelectModal(self.db_pool, owned_ids)
		await interaction.response.send_modal(modal)

	async def inventory_callback(self, interaction: discord.Interaction):
		if interaction.user.id != self.author.id:
			return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
		await interaction.response.send_message("背包功能正在施工中...", ephemeral=True)


__all__ = ["ProfileContainerView", "TitleSelectModal"]
