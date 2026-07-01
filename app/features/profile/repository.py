import time

import aiosqlite


async def get_citizen(db_pool: aiosqlite.Connection, user_id: int):
    async with db_pool.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
        return await cursor.fetchone()


async def create_citizen(
    db_pool: aiosqlite.Connection,
    user_id: int,
    name: str,
    species: str,
    pattern: str,
    money: float,
):
    await db_pool.execute(
        "INSERT INTO users (user_id, cat_name, cat_species, cat_pattern, money, status, active_title) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, name, species, pattern, money, "normal", "无名之辈"),
    )
    await db_pool.commit()


async def update_money(db_pool: aiosqlite.Connection, user_id: int, amount: float):
    await db_pool.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
    await db_pool.commit()


async def get_user_titles(db_pool: aiosqlite.Connection, user_id: int):
    async with db_pool.execute("SELECT title_id FROM user_titles WHERE user_id = ?", (user_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]


async def check_title_owned(db_pool: aiosqlite.Connection, user_id: int, title_id: str):
    async with db_pool.execute(
        "SELECT 1 FROM user_titles WHERE user_id = ? AND title_id = ?",
        (user_id, title_id),
    ) as cursor:
        return await cursor.fetchone() is not None


async def unlock_title(db_pool: aiosqlite.Connection, user_id: int, title_id: str):
    await db_pool.execute(
        "INSERT INTO user_titles (user_id, title_id, obtained_at) VALUES (?, ?, ?)",
        (user_id, title_id, int(time.time())),
    )
    await db_pool.commit()


async def equip_title(db_pool: aiosqlite.Connection, user_id: int, title_name: str):
    await db_pool.execute("UPDATE users SET active_title = ? WHERE user_id = ?", (title_name, user_id))
    await db_pool.commit()


__all__ = [
    "check_title_owned",
    "create_citizen",
    "equip_title",
    "get_citizen",
    "get_user_titles",
    "unlock_title",
    "update_money",
]
