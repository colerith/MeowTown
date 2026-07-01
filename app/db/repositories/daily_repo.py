import datetime

import aiosqlite

from app.db.engine import DB_PATH


async def get_daily_signin(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, last_signin_date, total_signin_count, last_reward, updated_at FROM daily_signins WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchone()


async def record_daily_signin(user_id, signin_date, reward_amount):
    updated_at = datetime.datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO daily_signins (user_id, last_signin_date, total_signin_count, last_reward, updated_at)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_signin_date = excluded.last_signin_date,
                total_signin_count = daily_signins.total_signin_count + 1,
                last_reward = excluded.last_reward,
                updated_at = excluded.updated_at
            """,
            (user_id, signin_date, reward_amount, updated_at),
        )
        await db.commit()


async def count_daily_signins_by_date(signin_date):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM daily_signins WHERE last_signin_date = ?",
            (signin_date,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


__all__ = ["count_daily_signins_by_date", "get_daily_signin", "record_daily_signin"]
