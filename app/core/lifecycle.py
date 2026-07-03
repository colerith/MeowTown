import discord
from discord.ext import commands

from app.core.command_sync import sync_and_log_commands
from app.db.engine import setup_db
from app.db.repositories.economy_repo import maybe_apply_global_economy_guard
from app.db.repositories.user_repo import sync_all_citizen_levels


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
            synced_count = await sync_all_citizen_levels()
            auto_guard_result = await maybe_apply_global_economy_guard(source="startup_ready")
            if getattr(bot, "db_ready_event", None):
                bot.db_ready_event.set()
            logger.info("✅ 数据库连接成功，表结构已更新。")
            logger.info(f"📊 市民等级同步完成，共处理 {synced_count} 位市民。")
            if auto_guard_result is not None:
                logger.warning(
                    "🌐 启动阶段自动经济熔断已执行 | before=%s | after=%s | changed_rows=%s",
                    auto_guard_result["total_before"],
                    auto_guard_result["total_after"],
                    auto_guard_result["changed_rows"],
                )
        except Exception as exc:
            logger.critical(f"🔥 数据库初始化失败: {exc}")

        try:
            async with bot.command_sync_lock:
                logger.info("🌐 正在执行启动阶段应用命令全局同步...")
                await sync_and_log_commands(bot, logger, force=True)
        except Exception as exc:
            logger.error(f"❌ 启动阶段应用命令同步失败: {exc}", exc_info=True)

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
                "🚫 **访问被拒绝**\n你还没有领养喵喵！请先使用 `/喵喵小镇 注册` 办理入住手续。",
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
