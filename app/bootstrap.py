import sys

import discord

from app.config.settings import load_settings
from app.core.bot import create_bot, setup_logging
from app.core.lifecycle import register_lifecycle_events
from app.core.loader import load_extensions


def run() -> None:
    logger = setup_logging()
    settings = load_settings()

    if not settings.token:
        logger.critical("❌ 错误: 未在 .env 文件中找到 DISCORD_TOKEN！")
        sys.exit(1)

    bot = create_bot(owner_ids=settings.owner_ids)
    register_lifecycle_events(bot, logger, settings.owner_ids)
    load_extensions(bot, logger)

    try:
        bot.run(settings.token)
    except discord.errors.LoginFailure:
        logger.critical("❌ 错误: Discord Token 无效！请检查 .env 文件。")
    except Exception as exc:
        logger.critical(f"❌ 启动时发生致命错误: {exc}")
