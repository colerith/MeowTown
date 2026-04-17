import datetime
import os
import shutil

import discord
from discord.ext import commands


class Admin(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	admin = discord.SlashCommandGroup("管理员", "管理员专用指令")

	@admin.command(name="备份数据", description="【仅限管理员】导出当前数据库文件")
	@commands.is_owner()
	async def backup(self, ctx: discord.ApplicationContext):
		db_source = "./data/meowtown.db"

		if not os.path.exists(db_source):
			await ctx.respond("🚫 数据库文件不存在！", ephemeral=True)
			return

		timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
		backup_filename = f"backup_{timestamp}.db"
		shutil.copy2(db_source, backup_filename)

		file_size = os.path.getsize(backup_filename) / (1024 * 1024)

		if file_size > 8:
			await ctx.respond(
				f"⚠️ 数据库文件过大 ({file_size:.2f}MB)，无法通过 Discord 发送。请使用 SCP/FTP 下载。",
				ephemeral=True,
			)
		else:
			try:
				file = discord.File(backup_filename, filename=f"meowtown_{timestamp}.db")
				await ctx.respond(
					f"✅ **数据备份成功**\n时间: {timestamp}\n大小: {file_size:.2f} MB",
					file=file,
					ephemeral=True,
				)
			except Exception as exc:
				await ctx.respond(f"🚫 发送失败: {exc}", ephemeral=True)

		os.remove(backup_filename)

	@backup.error
	async def on_error(self, ctx, error):
		if isinstance(error, commands.NotOwner):
			await ctx.respond("🚫 只有 Bot 的主人可以使用此指令！", ephemeral=True)
		else:
			raise error


def setup(bot):
	bot.add_cog(Admin(bot))
