import datetime
import logging
import os
import shutil

import discord
from discord.ext import commands

from app.cogs.gameplay.cat import TOWN_GROUP, register_town_group_command
from app.core.command_sync import summarize_pending_commands, summarize_registered_commands, sync_and_log_commands


class Admin(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.logger = getattr(bot, "meowtown_logger", logging.getLogger("喵喵小镇"))

	@commands.slash_command(name="同步命令", description="【仅限管理员】全局同步 Discord 应用命令")
	@commands.is_owner()
	async def sync_commands_global(self, ctx: discord.ApplicationContext):
		await ctx.defer(ephemeral=True)

		try:
			async with self.bot.command_sync_lock:
				self.logger.info(
					f"🛠️ 管理员 {ctx.author} ({ctx.author.id}) 手动触发了全局命令同步"
				)
				await sync_and_log_commands(self.bot, self.logger, force=True)
		except Exception as exc:
			self.logger.error(f"❌ 手动全局命令同步失败: {exc}", exc_info=True)
			return await ctx.followup.send(f"🚫 命令同步失败：{exc}", ephemeral=True)

		pending_lines = "\n".join(summarize_pending_commands(self.bot))
		registered_lines = "\n".join(summarize_registered_commands(self.bot))
		await ctx.followup.send(
			"✅ 已执行全局命令同步。\n"
			f"待同步快照：\n```text\n{pending_lines}\n```\n"
			f"当前挂载快照：\n```text\n{registered_lines}\n```",
			ephemeral=True,
		)

	@TOWN_GROUP.command(name="备份数据", description="【仅限管理员】导出当前数据库文件")
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

	@sync_commands_global.error
	async def on_sync_commands_global_error(self, ctx, error):
		if isinstance(error, commands.NotOwner):
			await ctx.respond("🚫 只有 Bot 的主人可以使用此指令！", ephemeral=True)
		else:
			raise error


def setup(bot):
	register_town_group_command(bot, Admin.backup)
	bot.add_cog(Admin(bot))
