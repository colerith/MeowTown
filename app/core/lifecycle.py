import discord
from discord.ext import commands

from app.db.engine import setup_db


def register_lifecycle_events(bot: discord.Bot, logger, owner_ids: list[int]) -> None:
    @bot.event
    async def on_ready() -> None:
        if getattr(bot, "db_ready_event", None) and bot.db_ready_event.is_set():
            activity = discord.Game(name="/帮助 | 喵喵小镇 V1.0")
            await bot.change_presence(status=discord.Status.online, activity=activity)
            logger.info("🚀 喵喵小镇机器人已完全就绪，开始提供服务！")
            return

        logger.info("🟢 机器人已成功连接到 Discord 网关！")
        logger.info(f"🤖 当前登录用户: {bot.user} (ID: {bot.user.id})")
        logger.info(f"🌍 加入服务器数: {len(bot.guilds)} 个")
        logger.info(f"👑 管理员 ID:   {owner_ids}")

        try:
            logger.info("💾 正在连接数据库...")
            await setup_db()
            if getattr(bot, "db_ready_event", None):
                bot.db_ready_event.set()
            logger.info("✅ 数据库连接成功，表结构已更新。")
        except Exception as exc:
            logger.critical(f"🔥 数据库初始化失败: {exc}")

        activity = discord.Game(name="/帮助 | 喵喵小镇 V1.0")
        await bot.change_presence(status=discord.Status.online, activity=activity)
        logger.info("🚀 喵喵小镇机器人已完全就绪，开始提供服务！")

    @bot.event
    async def on_application_command_error(
        ctx: discord.ApplicationContext,
        error: Exception,
    ) -> None:
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, discord.errors.CheckFailure):
            await ctx.respond(
                "🚫 **访问被拒绝**\n你还没有领养喵喵！请先使用 `/市民 注册` 办理入住手续。",
                ephemeral=True,
            )
            cmd_name = ctx.command.name if ctx.command else "未知命令"
            logger.warning(
                f"⚠️  警告: 用户 {ctx.author} 尝试在未注册情况下使用命令 '{cmd_name}'"
            )
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(
                f"⏳ 太快了！请等待 {error.retry_after:.1f} 秒后再试。",
                ephemeral=True,
            )
            return

        command_name = ctx.command.name if ctx.command else "未知命令"
        logger.error(f"❌ 执行命令 '/{command_name}' 时发生错误:")
        logger.error(f"   用户: {ctx.author} ({ctx.author.id})")
        logger.error(f"   异常信息: {error}", exc_info=True)

        try:
            await ctx.respond("💥 **系统错误**\n机器人遇到了一些问题，请联系管理员。", ephemeral=True)
        except Exception:
            pass
