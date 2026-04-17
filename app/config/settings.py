import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    token: str | None
    owner_ids: list[int]


def _parse_owner_ids(raw: str | None) -> list[int]:
    if not raw:
        return [1353777207042113576]

    values: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if item.isdigit():
            values.append(int(item))
    return values or [1353777207042113576]


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        token=os.getenv("DISCORD_TOKEN"),
        owner_ids=_parse_owner_ids(os.getenv("OWNER_IDS")),
    )
