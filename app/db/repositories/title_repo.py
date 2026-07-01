import time

import aiosqlite

from app.db.engine import DB_PATH


async def unlock_title(user_id, title_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_titles (user_id, title_id, obtained_at) VALUES (?, ?, ?)",
            (user_id, title_id, int(time.time())),
        )
        await db.commit()


async def check_title_owned(user_id, title_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM user_titles WHERE user_id = ? AND title_id = ?", (user_id, title_id))
        return await cursor.fetchone() is not None


async def equip_user_title(user_id, title_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET active_title = ? WHERE user_id = ?", (title_name, user_id))
        await db.commit()


async def get_user_titles(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT title_id FROM user_titles WHERE user_id = ?", (user_id,))
        return [row[0] for row in await cursor.fetchall()]


__all__ = [
    "check_title_owned",
    "equip_user_title",
    "get_user_titles",
    "unlock_title",
]
