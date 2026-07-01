import aiosqlite

from app.db.engine import DB_PATH


async def get_farm_state(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM farms WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                for plot_id in range(4):
                    await db.execute("INSERT INTO farms (user_id, plot_id) VALUES (?, ?)", (user_id, plot_id))
                await db.commit()
                async with db.execute("SELECT * FROM farms WHERE user_id = ?", (user_id,)) as cursor2:
                    rows = await cursor2.fetchall()
            return rows


async def plant_seed(user_id, plot_id, plant_id, current_time):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE farms SET plant_id = ?, planted_at = ?, is_notified = 0 WHERE user_id = ? AND plot_id = ?",
            (plant_id, current_time, user_id, plot_id),
        )
        await db.commit()


async def clear_plot(user_id, plot_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE farms SET plant_id = NULL, planted_at = NULL, is_notified = 0 WHERE user_id = ? AND plot_id = ?",
            (user_id, plot_id),
        )
        await db.commit()


async def add_farm_plot(user_id, plot_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO farms (user_id, plot_id) VALUES (?, ?)", (user_id, plot_id))
        await db.commit()


async def get_all_active_farms():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, plant_id, planted_at FROM farms WHERE plant_id IS NOT NULL AND is_notified = 0"
        ) as cursor:
            return await cursor.fetchall()


async def mark_farm_notified(user_id, plant_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE farms SET is_notified = 1 WHERE user_id = ? AND plant_id = ?", (user_id, plant_id))
        await db.commit()


async def accelerate_farm_growth(user_id, seconds):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE farms SET planted_at = planted_at - ? WHERE user_id = ? AND plant_id IS NOT NULL",
            (seconds, user_id),
        )
        await db.commit()


__all__ = [
    "accelerate_farm_growth",
    "add_farm_plot",
    "clear_plot",
    "get_all_active_farms",
    "get_farm_state",
    "mark_farm_notified",
    "plant_seed",
]
