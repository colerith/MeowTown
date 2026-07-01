import aiosqlite

from app.db.engine import DB_PATH


async def get_citizen(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def create_citizen(user_id, name, species, pattern, money):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, cat_name, cat_species, cat_pattern, money, status) VALUES (?, ?, ?, ?, ?, 'normal')",
            (user_id, name, species, pattern, money),
        )
        await db.commit()


async def update_citizen_look(user_id, species, pattern):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET cat_species = ?, cat_pattern = ? WHERE user_id = ?",
            (species, pattern, user_id),
        )
        await db.commit()


async def update_citizen_name(user_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET cat_name = ? WHERE user_id = ?", (name, user_id))
        await db.commit()


async def update_money(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def set_user_status(user_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        await db.commit()


async def equip_accessory(user_id, icon):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET cat_accessory = ? WHERE user_id = ?", (icon, user_id))
        await db.commit()


async def get_equipped_accessory(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT cat_accessory FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_user_money(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0.0


async def get_user(user_id):
    return await get_citizen(user_id)


async def list_registered_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users ORDER BY user_id")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


__all__ = [
    "create_citizen",
    "equip_accessory",
    "get_equipped_accessory",
    "get_citizen",
    "get_user_money",
    "get_user",
    "list_registered_user_ids",
    "set_user_status",
    "update_citizen_look",
    "update_citizen_name",
    "update_money",
]
