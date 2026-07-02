import aiosqlite

from app.db.engine import DB_PATH


async def get_top_money_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, cat_name, money FROM users ORDER BY money DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_property_owners(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT u.user_id, u.cat_name, COUNT(p.map_id) as count
            FROM monopoly_properties p
            JOIN users u ON p.owner_id = u.user_id
            GROUP BY p.owner_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_casino_winners(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT
                u.user_id,
                u.cat_name,
                s.wins,
                s.losses
            FROM casino_game_stats s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.wins > 0 OR s.losses > 0
            ORDER BY s.wins DESC, s.losses ASC, u.user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_jail_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT
                u.user_id,
                u.cat_name,
                s.jail_count
            FROM casino_game_stats s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.jail_count > 0
            ORDER BY s.jail_count DESC, u.user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_bank_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT
                u.user_id,
                u.cat_name,
                b.checking_balance + b.savings_balance AS total_deposit,
                b.checking_balance,
                b.savings_balance
            FROM casino_bank_accounts b
            JOIN users u ON b.user_id = u.user_id
            WHERE b.checking_balance + b.savings_balance > 0
            ORDER BY total_deposit DESC, b.savings_balance DESC, u.user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_robbery_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT
                u.user_id,
                u.cat_name,
                c.player_rob_success_count,
                c.bank_rob_success_count,
                c.robbery_loot_total
            FROM casino_crime_stats c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.player_rob_success_count > 0
               OR c.bank_rob_success_count > 0
               OR c.robbery_loot_total > 0
            ORDER BY
                (c.player_rob_success_count + c.bank_rob_success_count) DESC,
                c.robbery_loot_total DESC,
                u.user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_farm_steal_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT
                u.user_id,
                u.cat_name,
                f.steal_success_count,
                f.steal_fail_count,
                f.steal_income_total
            FROM farm_theft_stats f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.steal_success_count > 0
               OR f.steal_fail_count > 0
               OR f.steal_income_total > 0
            ORDER BY f.steal_success_count DESC, f.steal_income_total DESC, u.user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


__all__ = [
    "get_top_money_users",
    "get_top_property_owners",
    "get_top_casino_winners",
    "get_top_jail_users",
    "get_top_bank_users",
    "get_top_robbery_users",
    "get_top_farm_steal_users",
]
