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


async def get_all_farming_users(exclude_user_id=None):
    query = "SELECT DISTINCT user_id FROM farms WHERE plant_id IS NOT NULL"
    params = ()
    if exclude_user_id is not None:
        query += " AND user_id != ?"
        params = (exclude_user_id,)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            return [row[0] for row in await cursor.fetchall()]


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


async def set_farm_guard(user_id, guard_type, expires_at):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO farm_guards (user_id, guard_type, expires_at, expired_notice_sent) VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                guard_type = excluded.guard_type,
                expires_at = excluded.expires_at,
                expired_notice_sent = 0
            """,
            (user_id, guard_type, expires_at),
        )
        await db.commit()


async def get_farm_guard(user_id, current_time=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT guard_type, expires_at FROM farm_guards WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        if current_time is not None and row[1] <= current_time:
            return None

        return row


async def get_expired_farm_guards(current_time):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT user_id, guard_type, expires_at
            FROM farm_guards
            WHERE expires_at <= ? AND expired_notice_sent = 0
            ORDER BY expires_at
            """,
            (current_time,),
        )
        return await cursor.fetchall()


async def mark_farm_guard_notice_sent(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE farm_guards SET expired_notice_sent = 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def remove_farm_guard(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM farm_guards WHERE user_id = ?", (user_id,))
        await db.commit()


async def clear_expired_farm_guards(current_time):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM farm_guards WHERE expires_at <= ?", (current_time,))
        await db.commit()


async def record_farm_steal_result(user_id, *, success: bool, income: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO farm_theft_stats (
                user_id, steal_success_count, steal_fail_count, steal_income_total
            ) VALUES (?, 0, 0, 0)
            """,
            (user_id,),
        )
        if success:
            await db.execute(
                """
                UPDATE farm_theft_stats
                SET steal_success_count = steal_success_count + 1,
                    steal_income_total = steal_income_total + ?
                WHERE user_id = ?
                """,
                (income, user_id),
            )
        else:
            await db.execute(
                """
                UPDATE farm_theft_stats
                SET steal_fail_count = steal_fail_count + 1
                WHERE user_id = ?
                """,
                (user_id,),
            )
        await db.commit()


__all__ = [
    "accelerate_farm_growth",
    "add_farm_plot",
    "clear_expired_farm_guards",
    "clear_plot",
    "get_expired_farm_guards",
    "get_all_active_farms",
    "get_all_farming_users",
    "get_farm_guard",
    "get_farm_state",
    "mark_farm_guard_notice_sent",
    "mark_farm_notified",
    "plant_seed",
    "record_farm_steal_result",
    "remove_farm_guard",
    "set_farm_guard",
]
