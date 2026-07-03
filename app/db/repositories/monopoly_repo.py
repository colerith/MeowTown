import aiosqlite

from app.db.engine import DB_PATH
from app.db.repositories.user_repo import apply_money_delta_with_db

DEFAULT_PROPERTY_MAINTENANCE_INTERVAL = 7 * 24 * 60 * 60


async def ensure_player(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT position, status, jail_turns_left, next_dice_fixed, bad_luck_count FROM monopoly_players WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row:
            return row

        await db.execute("INSERT INTO monopoly_players (user_id, bad_luck_count) VALUES (?, 0)", (user_id,))
        await db.commit()
        return (0, "normal", 0, 0, 0)


async def get_player_state(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT position, status, jail_turns_left, next_dice_fixed, bad_luck_count FROM monopoly_players WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchone()


async def activate_next_dice_fixed(user_id, value=6):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE monopoly_players SET next_dice_fixed = ? WHERE user_id = ?",
            (value, user_id),
        )
        await db.commit()


async def clear_next_dice_fixed(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE monopoly_players SET next_dice_fixed = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_player_position(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT position FROM monopoly_players WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_property_owner(map_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT owner_id FROM monopoly_properties WHERE map_id = ?",
            (map_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_property_state(map_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT owner_id, level, effect, purchase_price, maintenance_due_at FROM monopoly_properties WHERE map_id = ?",
            (map_id,),
        )
        return await cursor.fetchone()


async def get_owned_properties(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT map_id, level, maintenance_due_at FROM monopoly_properties WHERE owner_id = ? ORDER BY map_id",
            (user_id,),
        )
        return await cursor.fetchall()


async def get_owned_property_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM monopoly_properties WHERE owner_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def upgrade_property(user_id, map_id, cost):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        money = row[0] if row else 0
        if money < cost:
            return False, money

        await apply_money_delta_with_db(db, user_id, -cost, economy_mode="direct")
        await db.execute("UPDATE monopoly_properties SET level = level + 1 WHERE map_id = ?", (map_id,))
        await db.commit()
        return True, money


async def decrement_jail_turn_and_add_bad_luck(user_id, turns_left):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE monopoly_players SET jail_turns_left = ? WHERE user_id = ?", (turns_left - 1, user_id))
        await db.execute("UPDATE monopoly_players SET bad_luck_count = bad_luck_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def move_player(user_id, position):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE monopoly_players SET position = ? WHERE user_id = ?", (position, user_id))
        await db.commit()


async def move_player_with_pass_go(user_id, old_position, roll, map_size, pass_go_salary):
    new_position = (old_position + roll) % map_size
    passed_go = new_position < old_position
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE monopoly_players SET position = ? WHERE user_id = ?", (new_position, user_id))
        if passed_go:
            await apply_money_delta_with_db(db, user_id, pass_go_salary, economy_mode="gameplay")
        await db.commit()
    return new_position, passed_go


async def pay_rent(user_id, owner_id, amount, map_id=None, clear_roadblock=False):
    async with aiosqlite.connect(DB_PATH) as db:
        if clear_roadblock and map_id is not None:
            await db.execute("UPDATE monopoly_properties SET effect = NULL WHERE map_id = ?", (map_id,))
        await apply_money_delta_with_db(db, user_id, -amount, economy_mode="direct")
        await apply_money_delta_with_db(db, owner_id, amount, economy_mode="gameplay")
        await db.commit()


async def buy_property(user_id, map_id, price):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT owner_id FROM monopoly_properties WHERE map_id = ?", (map_id,))
        if await cursor.fetchone():
            return False, "owned"

        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        money = row[0] if row else 0
        if money < price:
            return False, "insufficient"

        cursor = await db.execute("SELECT strftime('%s','now')")
        now_ts = int((await cursor.fetchone())[0])
        await apply_money_delta_with_db(db, user_id, -price, economy_mode="direct")
        await db.execute(
            """
            INSERT INTO monopoly_properties (map_id, owner_id, level, purchase_price, maintenance_due_at, maintenance_notice_sent)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (map_id, user_id, 1, price, now_ts + DEFAULT_PROPERTY_MAINTENANCE_INTERVAL),
        )
        await db.commit()
        return True, None


async def maintain_all_properties(user_id, fee_per_property, next_due_at):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT map_id, purchase_price FROM monopoly_properties WHERE owner_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        property_count = len(rows)
        if property_count == 0:
            return False, "no_properties", 0

        total_fee = property_count * fee_per_property
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        money = row[0] if row else 0
        if money < total_fee:
            return False, "insufficient", total_fee

        await apply_money_delta_with_db(db, user_id, -total_fee, economy_mode="direct")
        await db.execute(
            """
            UPDATE monopoly_properties
            SET maintenance_due_at = ?, maintenance_notice_sent = 0
            WHERE owner_id = ?
            """,
            (next_due_at, user_id),
        )
        await db.commit()
        return True, rows, total_fee


async def pay_bail(user_id, bail_cost):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        money = row[0] if row else 0
        if money < bail_cost:
            return False, money

        await apply_money_delta_with_db(db, user_id, -bail_cost, economy_mode="direct")
        await db.execute(
            "UPDATE monopoly_players SET status = 'normal', jail_turns_left = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
        return True, money


async def bankrupt_player(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = 0 WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM monopoly_properties WHERE owner_id = ?", (user_id,))
        await db.execute("UPDATE monopoly_players SET position = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def release_from_jail(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE monopoly_players SET status = 'normal', jail_turns_left = 0 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def send_player_to_jail(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE monopoly_players SET position = 10, status = 'in_jail', jail_turns_left = 3 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def place_roadblock(map_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE monopoly_properties SET effect = 'roadblock' WHERE map_id = ?",
            (map_id,),
        )
        await db.commit()


async def get_properties_needing_maintenance_notice(current_time, reminder_threshold):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT map_id, owner_id, level, purchase_price, maintenance_due_at
            FROM monopoly_properties
            WHERE owner_id IS NOT NULL
              AND maintenance_due_at > ?
              AND maintenance_due_at <= ?
              AND maintenance_notice_sent = 0
            ORDER BY maintenance_due_at ASC
            """,
            (current_time, current_time + reminder_threshold),
        )
        return await cursor.fetchall()


async def mark_property_maintenance_notice_sent(map_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE monopoly_properties SET maintenance_notice_sent = 1 WHERE map_id = ?",
            (map_id,),
        )
        await db.commit()


async def reclaim_expired_properties(current_time, refund_ratio):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT map_id, owner_id, purchase_price
            FROM monopoly_properties
            WHERE owner_id IS NOT NULL AND maintenance_due_at > 0 AND maintenance_due_at <= ?
            """,
            (current_time,),
        )
        rows = await cursor.fetchall()
        reclaimed = []
        for map_id, owner_id, purchase_price in rows:
            refund = round(float(purchase_price or 0) * refund_ratio, 2)
            if refund > 0:
                await apply_money_delta_with_db(db, owner_id, refund, economy_mode="gameplay")
            await db.execute("DELETE FROM monopoly_properties WHERE map_id = ?", (map_id,))
            reclaimed.append((map_id, owner_id, float(purchase_price or 0), refund))
        await db.commit()
        return reclaimed


__all__ = [
    "activate_next_dice_fixed",
    "bankrupt_player",
    "buy_property",
    "clear_next_dice_fixed",
    "decrement_jail_turn_and_add_bad_luck",
    "ensure_player",
    "get_owned_property_count",
    "get_owned_properties",
    "get_player_state",
    "get_player_position",
    "get_properties_needing_maintenance_notice",
    "get_property_owner",
    "get_property_state",
    "maintain_all_properties",
    "mark_property_maintenance_notice_sent",
    "move_player",
    "move_player_with_pass_go",
    "pay_bail",
    "pay_rent",
    "place_roadblock",
    "reclaim_expired_properties",
    "release_from_jail",
    "send_player_to_jail",
    "upgrade_property",
]
