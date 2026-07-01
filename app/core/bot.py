import logging

import discord


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("喵喵小镇")


def create_bot(owner_ids: list[int]) -> discord.Bot:
    intents = discord.Intents.default()
    intents.members = True
    return discord.Bot(owner_ids=owner_ids, intents=intents)
