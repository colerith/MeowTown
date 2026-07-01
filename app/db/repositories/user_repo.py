import math

import aiosqlite

from app.db.engine import DB_PATH


LEVEL_SCORE_FACTOR = 120
MAX_CITIZEN_LEVEL = 999


def calculate_citizen_level(score):
    safe_score = max(0, int(score))
    level = int(math.sqrt(safe_score / LEVEL_SCORE_FACTOR)) + 1
    return max(1, min(MAX_CITIZEN_LEVEL, level))


def calculate_level_threshold(level):
    safe_level = max(1, min(MAX_CITIZEN_LEVEL, int(level)))
    return int((safe_level - 1) ** 2 * LEVEL_SCORE_FACTOR)


def calculate_next_level_threshold(level):
    safe_level = max(1, min(MAX_CITIZEN_LEVEL, int(level)))
    if safe_level >= MAX_CITIZEN_LEVEL:
        return calculate_level_threshold(MAX_CITIZEN_LEVEL)
    return int(safe_level ** 2 * LEVEL_SCORE_FACTOR)


def build_level_score_from_stats(stats):
    cash = max(0, float(stats["cash"]))
    stock_value = max(0, float(stats["stock_value"]))
    property_purchase_total = max(0, float(stats["property_purchase_total"]))
    loan_amount = max(0, float(stats["loan_amount"]))

    score = (
        cash
        + stock_value
        + property_purchase_total * 0.35
        + stats["property_count"] * 2000
        + stats["property_levels"] * 800
        + stats["farm_plot_count"] * 500
        + stats["active_crop_count"] * 250
        + stats["title_count"] * 1200
        + stats["signin_count"] * 180
        + stats["stock_share_count"] * 6
        - loan_amount * 0.5
    )
    return max(0, int(score))


async def _fetch_profile_stats(db, user_id):
    cursor = await db.execute(
        """
        SELECT
            COALESCE(u.money, 0),
            COALESCE((SELECT SUM(p.quantity * s.current_price) FROM portfolios p JOIN stocks s ON s.stock_id = p.stock_id WHERE p.user_id = u.user_id), 0),
            COALESCE((SELECT COUNT(*) FROM monopoly_properties WHERE owner_id = u.user_id), 0),
            COALESCE((SELECT SUM(level) FROM monopoly_properties WHERE owner_id = u.user_id), 0),
            COALESCE((SELECT SUM(purchase_price) FROM monopoly_properties WHERE owner_id = u.user_id), 0),
            COALESCE((SELECT COUNT(*) FROM farms WHERE user_id = u.user_id), 0),
            COALESCE((SELECT COUNT(*) FROM farms WHERE user_id = u.user_id AND plant_id IS NOT NULL), 0),
            COALESCE((SELECT COUNT(*) FROM user_titles WHERE user_id = u.user_id), 0),
            COALESCE((SELECT total_signin_count FROM daily_signins WHERE user_id = u.user_id), 0),
            COALESCE((SELECT loan_amount FROM loans WHERE user_id = u.user_id), 0),
            COALESCE((SELECT SUM(quantity) FROM portfolios WHERE user_id = u.user_id), 0)
        FROM users u
        WHERE u.user_id = ?
        """,
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    return {
        "cash": float(row[0] or 0),
        "stock_value": float(row[1] or 0),
        "property_count": int(row[2] or 0),
        "property_levels": int(row[3] or 0),
        "property_purchase_total": float(row[4] or 0),
        "farm_plot_count": int(row[5] or 0),
        "active_crop_count": int(row[6] or 0),
        "title_count": int(row[7] or 0),
        "signin_count": int(row[8] or 0),
        "loan_amount": float(row[9] or 0),
        "stock_share_count": int(row[10] or 0),
    }


async def _sync_citizen_level_with_db(db, user_id):
    stats = await _fetch_profile_stats(db, user_id)
    if stats is None:
        return None

    level_score = build_level_score_from_stats(stats)
    citizen_level = calculate_citizen_level(level_score)
    await db.execute(
        "UPDATE users SET citizen_level = ?, level_score = ? WHERE user_id = ?",
        (citizen_level, level_score, user_id),
    )
    return citizen_level, level_score, stats


async def sync_citizen_level(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        result = await _sync_citizen_level_with_db(db, user_id)
        await db.commit()
        return result


async def sync_all_citizen_levels():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users ORDER BY user_id")
        user_ids = [row[0] for row in await cursor.fetchall()]
        for user_id in user_ids:
            await _sync_citizen_level_with_db(db, user_id)
        await db.commit()
        return len(user_ids)


async def get_citizen(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await _sync_citizen_level_with_db(db, user_id)
        await db.commit()
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()


async def create_citizen(user_id, name, species, pattern, money):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (
                user_id, cat_name, cat_species, cat_pattern, money, status,
                active_title, citizen_level, level_score
            ) VALUES (?, ?, ?, ?, ?, 'normal', '无名之辈', 1, 0)
            """,
            (user_id, name, species, pattern, money),
        )
        await _sync_citizen_level_with_db(db, user_id)
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
        await _sync_citizen_level_with_db(db, user_id)
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


async def get_citizen_profile_summary(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        sync_result = await _sync_citizen_level_with_db(db, user_id)
        if sync_result is None:
            return None

        citizen_level, level_score, stats = sync_result
        await db.commit()
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        citizen = await cursor.fetchone()
        net_worth = stats["cash"] + stats["stock_value"] - stats["loan_amount"]
        current_threshold = calculate_level_threshold(citizen_level)
        next_threshold = calculate_next_level_threshold(citizen_level)

        return {
            "citizen": citizen,
            "level": citizen_level,
            "level_score": level_score,
            "current_threshold": current_threshold,
            "next_threshold": next_threshold,
            "progress_in_level": max(0, level_score - current_threshold),
            "progress_needed": max(1, next_threshold - current_threshold) if citizen_level < MAX_CITIZEN_LEVEL else 1,
            "net_worth": net_worth,
            **stats,
        }


async def get_user(user_id):
    return await get_citizen(user_id)


async def list_registered_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users ORDER BY user_id")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


__all__ = [
    "MAX_CITIZEN_LEVEL",
    "LEVEL_SCORE_FACTOR",
    "build_level_score_from_stats",
    "calculate_citizen_level",
    "calculate_level_threshold",
    "calculate_next_level_threshold",
    "create_citizen",
    "equip_accessory",
    "get_citizen",
    "get_citizen_profile_summary",
    "get_equipped_accessory",
    "get_user_money",
    "get_user",
    "list_registered_user_ids",
    "set_user_status",
    "sync_all_citizen_levels",
    "sync_citizen_level",
    "update_citizen_look",
    "update_citizen_name",
    "update_money",
]
