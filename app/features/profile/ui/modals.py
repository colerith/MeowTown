from typing import List

import discord
from discord import ui

from app.features.profile import repository
from app.features.profile import service


class TitleSelectModal(ui.Modal, title="更换称号"):
	def __init__(self, db_pool: discord.Bot, owned_title_ids: List[str]):
		super().__init__()
		self.db_pool = db_pool

		options = [discord.SelectOption(label="卸下称号", value="无名之辈", emoji="🚫")]
		for tid in owned_title_ids:
			title = service.TITLES.get(tid)
			if title:
				rarity = service.RARITY_CONFIG[title["rarity"]]["name"]
				options.append(
					discord.SelectOption(
						label=title["name"],
						value=title["name"],
						description=f"稀有度: {rarity}",
					)
				)

		self.title_select = ui.Label(
			text="选择一个你要佩戴的新称号:",
			component=ui.Select(
				custom_id="title_select",
				placeholder="请选择你的称号...",
				options=options,
			),
		)

	async def on_submit(self, interaction: discord.Interaction):
		new_title_name = self.title_select.component.values[0]
		await repository.equip_title(self.db_pool, interaction.user.id, new_title_name)
		await interaction.response.send_message(f"✅ 称号已更换为 **【{new_title_name}】**！", ephemeral=True)


__all__ = ["TitleSelectModal"]
