# cogs/admin.py
import discord
import os
import shutil
import datetime
from discord.ext import commands

# 设置只有机器人的拥有者才能使用此命令
# 你需要在 main.py 启动时设置 owner_id，或者 py-cord 会自动识别 application owner
class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin = discord.SlashCommandGroup("管理员", "管理员专用指令")

    @admin.command(name="备份数据", description="【仅限管理员】导出当前数据库文件")
    @commands.is_owner()  # 关键！只有Bot拥有者能运行
    async def backup(self, ctx: discord.ApplicationContext):
        # 数据库路径
        db_source = "./data/meowtown.db"
        
        if not os.path.exists(db_source):
            await ctx.respond("🚫 数据库文件不存在！", ephemeral=True)
            return

        # 1. 创建一个带时间戳的副本 (防止直接发送正在写入的文件导致损坏)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        shutil.copy2(db_source, backup_filename)

        # 2. 获取文件大小
        file_size = os.path.getsize(backup_filename) / (1024 * 1024) # MB

        # 3. 发送文件
        # Discord 普通上传限制是 10MB (Nitro 25MB/100MB/500MB)
        if file_size > 8: 
            await ctx.respond(f"⚠️ 数据库文件过大 ({file_size:.2f}MB)，无法通过 Discord 发送。请使用 SCP/FTP 下载。", ephemeral=True)
        else:
            try:
                file = discord.File(backup_filename, filename=f"meowtown_{timestamp}.db")
                await ctx.respond(f"✅ **数据备份成功**\n时间: {timestamp}\n大小: {file_size:.2f} MB", file=file, ephemeral=True)
            except Exception as e:
                await ctx.respond(f"🚫 发送失败: {e}", ephemeral=True)
        
        # 4. 清理临时文件
        os.remove(backup_filename)

    # 错误处理：如果不是拥有者调用，给予提示
    @backup.error
    async def on_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.respond("🚫 只有 Bot 的主人可以使用此指令！", ephemeral=True)
        else:
            raise error

def setup(bot):

    bot.add_cog(Admin(bot))
