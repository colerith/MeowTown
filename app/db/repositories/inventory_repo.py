import aiosqlite

from app.db.engine import DB_PATH


async def add_item(user_id, item_name, count=1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO monopoly_items (user_id, item_name, count) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, item_name) DO UPDATE SET count = count + excluded.count",
            (user_id, item_name, count),
        )
        await db.commit()


async def use_item_from_db(user_id, item_name):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count FROM monopoly_items WHERE user_id = ? AND item_name = ?",
            (user_id, item_name),
        )
        row = await cursor.fetchone()
        if not row or row[0] < 1:
            return False

        new_count = row[0] - 1
        if new_count == 0:
            await db.execute("DELETE FROM monopoly_items WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else:
            await db.execute(
                "UPDATE monopoly_items SET count = ? WHERE user_id = ? AND item_name = ?",
                (new_count, user_id, item_name),
            )
        await db.commit()
        return True


async def get_items(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT item_name, count FROM monopoly_items WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()


__all__ = ["add_item", "get_items", "use_item_from_db"]
