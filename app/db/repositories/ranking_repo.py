import aiosqlite

from app.db.engine import DB_PATH


async def get_top_money_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT cat_name, money FROM users ORDER BY money DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_top_property_owners(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT u.cat_name, COUNT(p.map_id) as count
            FROM monopoly_properties p
            JOIN users u ON p.owner_id = u.user_id
            GROUP BY p.owner_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


__all__ = ["get_top_money_users", "get_top_property_owners"]
