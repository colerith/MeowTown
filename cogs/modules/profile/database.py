# modules/profile/database.py
import aiosqlite

# --- 市民管理 ---
async def get_citizen(db_pool: aiosqlite.Connection, user_id: int):
    async with db_pool.execute("SELECT * FROM citizens WHERE user_id = ?", (user_id,)) as cursor:
        return await cursor.fetchone()

async def create_citizen(db_pool: aiosqlite.Connection, user_id: int, name: str, species: str, pattern: str, money: float):
    await db_pool.execute(
        "INSERT INTO citizens (user_id, name, species, pattern, money, active_title) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, species, pattern, money, "无名之辈")
    )
    await db_pool.commit()

async def update_money(db_pool: aiosqlite.Connection, user_id: int, amount: float):
    await db_pool.execute("UPDATE citizens SET money = money + ? WHERE user_id = ?", (amount, user_id))
    await db_pool.commit()

# --- 称号管理 ---
async def get_user_titles(db_pool: aiosqlite.Connection, user_id: int):
    async with db_pool.execute("SELECT title_id FROM user_titles WHERE user_id = ?", (user_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]

async def check_title_owned(db_pool: aiosqlite.Connection, user_id: int, title_id: str):
    async with db_pool.execute("SELECT 1 FROM user_titles WHERE user_id = ? AND title_id = ?", (user_id, title_id)) as cursor:
        return await cursor.fetchone() is not None

async def unlock_title(db_pool: aiosqlite.Connection, user_id: int, title_id: str):
    await db_pool.execute("INSERT INTO user_titles (user_id, title_id) VALUES (?, ?)", (user_id, title_id))
    await db_pool.commit()

async def equip_title(db_pool: aiosqlite.Connection, user_id: int, title_name: str):
    await db_pool.execute("UPDATE citizens SET active_title = ? WHERE user_id = ?", (title_name, user_id))
    await db_pool.commit()
