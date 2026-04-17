from __future__ import annotations

from pathlib import Path

import discord


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _discover_extensions() -> list[str]:
    extensions: list[str] = []
    migrated_stems: set[str] = set()

    # New structure: app/cogs/**/<module>.py
    new_cogs_root = PROJECT_ROOT / "app" / "cogs"
    if new_cogs_root.exists():
        for file_path in new_cogs_root.rglob("*.py"):
            if file_path.name == "__init__.py":
                continue
            relative_module = file_path.relative_to(PROJECT_ROOT).with_suffix("")
            extensions.append(".".join(relative_module.parts))
            migrated_stems.add(file_path.stem)

    # Backward-compatible fallback: existing cogs/*.py
    legacy_cogs_root = PROJECT_ROOT / "cogs"
    if legacy_cogs_root.exists():
        for file_path in legacy_cogs_root.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            if file_path.stem in migrated_stems:
                continue
            extensions.append(f"cogs.{file_path.stem}")

    return sorted(set(extensions))


def load_extensions(bot: discord.Bot, logger) -> None:
    logger.info("--------------------------------------------------")
    logger.info("🔄 正在启动插件加载程序...")

    extensions = _discover_extensions()
    for ext in extensions:
        try:
            bot.load_extension(ext)
            logger.info(f"✅ 加载插件成功: {ext}")
        except Exception as exc:
            logger.error(f"❌ 加载插件失败: {ext} | 错误: {exc}")

    logger.info(f"📦 扫描到的插件总数: {len(extensions)}")
    logger.info("--------------------------------------------------")
