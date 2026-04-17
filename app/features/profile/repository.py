"""Profile repository compatibility module."""

from cogs.modules.profile.database import (
    check_title_owned,
    create_citizen,
    equip_title,
    get_citizen,
    get_user_titles,
    unlock_title,
    update_money,
)

__all__ = [
    "check_title_owned",
    "create_citizen",
    "equip_title",
    "get_citizen",
    "get_user_titles",
    "unlock_title",
    "update_money",
]
