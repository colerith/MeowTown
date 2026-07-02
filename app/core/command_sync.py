from __future__ import annotations

from typing import Iterable


def get_town_group_commands(bot) -> list:
    command_specs = [
        ("Cat", "register"),
        ("Cat", "profile"),
        ("Cat", "compensation_config"),
        ("Cat", "reset_stock_market"),
        ("Cat", "backfill_registered_role"),
        ("Cat", "send_signin_panel"),
        ("Cat", "send_stock_panel"),
        ("Admin", "backup"),
        ("Announcement", "publish_announcement"),
        ("General", "help"),
        ("General", "ping"),
        ("Welfare", "welfare_drop"),
    ]
    commands: list = []
    for cog_name, command_attr in command_specs:
        cog = bot.get_cog(cog_name)
        if cog is None:
            continue
        command = getattr(cog, command_attr, None)
        if command is not None:
            commands.append(command)
    return commands


def sanitize_command_options(command) -> None:
    options = getattr(command, "options", None)
    if options is not None:
        command.options = [
            option
            for option in options
            if getattr(option, "input_type", None) is not None
        ]

    for subcommand in getattr(command, "subcommands", []) or []:
        sanitize_command_options(subcommand)


def ensure_town_group_pending_synced(bot) -> bool:
    try:
        from app.cogs.gameplay.cat import TOWN_GROUP
    except Exception:
        return False
    town_group_commands = get_town_group_commands(bot)
    TOWN_GROUP.subcommands = list(town_group_commands)
    sanitize_command_options(TOWN_GROUP)

    for pending_command in getattr(bot, "pending_application_commands", []):
        if getattr(pending_command, "name", None) != TOWN_GROUP.name:
            continue
        pending_command.subcommands = list(town_group_commands)
        for subcommand in pending_command.subcommands:
            subcommand.parent = pending_command
        sanitize_command_options(pending_command)
        return True
    return False


def _command_label(command) -> str:
    name = getattr(command, "name", "未知命令")
    command_type = getattr(command, "type", None)
    if command_type is not None:
        return f"{name}({command_type})"
    return str(name)


def summarize_pending_commands(bot) -> list[str]:
    pending_commands = list(getattr(bot, "pending_application_commands", []) or [])
    if not pending_commands:
        return ["无待注册应用命令"]

    lines: list[str] = [f"待注册顶级命令数: {len(pending_commands)}"]
    for command in pending_commands:
        subcommands: Iterable = getattr(command, "subcommands", []) or []
        subcommand_names = [getattr(subcommand, "name", "未知子命令") for subcommand in subcommands]
        if subcommand_names:
            joined = "、".join(subcommand_names)
            lines.append(f"- {_command_label(command)} -> {len(subcommand_names)} 个子命令: {joined}")
        else:
            lines.append(f"- {_command_label(command)}")
    return lines


def summarize_registered_commands(bot) -> list[str]:
    registered_commands = list(getattr(bot, "application_commands", []) or [])
    if not registered_commands:
        return ["当前 bot.application_commands 为空"]

    lines: list[str] = [f"已挂载应用命令数: {len(registered_commands)}"]
    for command in registered_commands:
        subcommands: Iterable = getattr(command, "subcommands", []) or []
        subcommand_names = [getattr(subcommand, "name", "未知子命令") for subcommand in subcommands]
        if subcommand_names:
            joined = "、".join(subcommand_names)
            lines.append(f"- {_command_label(command)} -> {len(subcommand_names)} 个子命令: {joined}")
        else:
            lines.append(f"- {_command_label(command)}")
    return lines


async def sync_and_log_commands(bot, logger, *, force: bool = True) -> None:
    ensure_town_group_pending_synced(bot)
    for pending_command in getattr(bot, "pending_application_commands", []) or []:
        sanitize_command_options(pending_command)
    logger.info("🧭 应用命令待同步快照开始")
    for line in summarize_pending_commands(bot):
        logger.info(f"   {line}")
    for line in summarize_registered_commands(bot):
        logger.info(f"   {line}")

    await bot.sync_commands(force=force)

    ensure_town_group_pending_synced(bot)
    logger.info("✅ 应用命令同步完成")
    for line in summarize_pending_commands(bot):
        logger.info(f"   {line}")
    for line in summarize_registered_commands(bot):
        logger.info(f"   {line}")
