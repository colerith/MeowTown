from __future__ import annotations

from datetime import datetime, timedelta

import aiosqlite

from app.db.engine import DB_PATH
from app.features.casino.service import get_utc_now


async def _ensure_casino_rows(db, user_id):
    await db.execute(
        """
        INSERT OR IGNORE INTO casino_bank_accounts (
            user_id, checking_balance, savings_balance, savings_locked_until
        ) VALUES (?, 0, 0, NULL)
        """,
        (user_id,),
    )
    await db.execute(
        """
        INSERT OR IGNORE INTO casino_jail_records (
            user_id, sentence_ends_at, bribes_today, last_bribe_date,
            robberies_today, robbery_successes_today, guard_duels_today, last_crime_date
        ) VALUES (?, NULL, 0, NULL, 0, 0, 0, NULL)
        """,
        (user_id,),
    )
    await db.execute(
        """
        INSERT OR IGNORE INTO casino_game_stats (
            user_id, wins, losses, jail_count
        ) VALUES (?, 0, 0, 0)
        """,
        (user_id,),
    )
    await db.execute(
        """
        INSERT OR IGNORE INTO casino_gambling_profiles (
            user_id, bet_mode, custom_bet, last_bet, random_min_percent, random_max_percent
        ) VALUES (?, 'random', 500, 0, 5, 15)
        """,
        (user_id,),
    )
    await db.execute(
        """
        INSERT OR IGNORE INTO casino_crime_stats (
            user_id, player_rob_success_count, bank_rob_success_count, robbery_loot_total
        ) VALUES (?, 0, 0, 0)
        """,
        (user_id,),
    )


async def ensure_casino_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.commit()


async def get_wallet_and_level(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT money, citizen_level FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return int(row["money"] or 0), int(row["citizen_level"] or 1)


async def get_bank_account(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.commit()
        cursor = await db.execute(
            """
            SELECT
                b.user_id,
                b.checking_balance,
                b.savings_balance,
                b.savings_locked_until,
                u.money
            FROM casino_bank_accounts b
            JOIN users u ON u.user_id = b.user_id
            WHERE b.user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return (
            row["user_id"],
            int(row["checking_balance"] or 0),
            int(row["savings_balance"] or 0),
            row["savings_locked_until"],
            int(row["money"] or 0),
        )


async def get_bank_leaderboard(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                user_id,
                checking_balance + savings_balance AS total_deposit
            FROM casino_bank_accounts
            WHERE checking_balance + savings_balance > 0
            ORDER BY total_deposit DESC, user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [(row["user_id"], int(row["total_deposit"] or 0)) for row in rows]


async def deposit_to_account(user_id, amount, account_type, locked_until=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        user_row = await cursor.fetchone()
        if user_row is None:
            return False, "user_missing", None

        wallet = int(user_row["money"] or 0)
        if wallet < amount:
            return False, "insufficient_wallet", wallet

        target_col = "checking_balance" if account_type == "checking" else "savings_balance"
        await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (amount, user_id))
        await db.execute(
            f"UPDATE casino_bank_accounts SET {target_col} = {target_col} + ? WHERE user_id = ?",
            (amount, user_id),
        )
        if account_type == "savings":
            await db.execute(
                "UPDATE casino_bank_accounts SET savings_locked_until = ? WHERE user_id = ?",
                (locked_until.isoformat() if locked_until else None, user_id),
            )
        await db.commit()
        return True, "ok", wallet


async def withdraw_from_account(user_id, amount, account_type, now=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute(
            """
            SELECT checking_balance, savings_balance, savings_locked_until
            FROM casino_bank_accounts
            WHERE user_id = ?
            """,
            (user_id,),
        )
        bank_row = await cursor.fetchone()
        if bank_row is None:
            return False, "account_missing", None

        target_col = "checking_balance" if account_type == "checking" else "savings_balance"
        balance = int(bank_row[target_col] or 0)
        if balance < amount:
            return False, "insufficient_bank", balance

        if account_type == "savings" and bank_row["savings_locked_until"]:
            locked_until = datetime.fromisoformat(bank_row["savings_locked_until"])
            now = now or get_utc_now()
            if now < locked_until:
                return False, "savings_locked", locked_until

        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        await db.execute(
            f"UPDATE casino_bank_accounts SET {target_col} = {target_col} - ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()
        return True, "ok", balance


async def get_casino_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.commit()
        cursor = await db.execute(
            """
            SELECT
                s.wins,
                s.losses,
                s.jail_count,
                j.sentence_ends_at,
                j.bribes_today,
                j.last_bribe_date,
                j.robberies_today,
                j.robbery_successes_today,
                j.guard_duels_today,
                j.last_crime_date
            FROM casino_game_stats s
            JOIN casino_jail_records j ON j.user_id = s.user_id
            WHERE s.user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return (
            int(row["wins"] or 0),
            int(row["losses"] or 0),
            int(row["jail_count"] or 0),
            row["sentence_ends_at"],
            int(row["bribes_today"] or 0),
            row["last_bribe_date"],
            int(row["robberies_today"] or 0),
            int(row["robbery_successes_today"] or 0),
            int(row["guard_duels_today"] or 0),
            row["last_crime_date"],
        )


async def get_daily_crime_counters(user_id, today):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute(
            """
            SELECT robberies_today, robbery_successes_today, guard_duels_today, last_crime_date
            FROM casino_jail_records
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return 0, 0, 0
        if row["last_crime_date"] != today:
            return 0, 0, 0
        return (
            int(row["robberies_today"] or 0),
            int(row["robbery_successes_today"] or 0),
            int(row["guard_duels_today"] or 0),
        )


async def consume_daily_robbery_attempt(user_id, today):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute(
            """
            SELECT robberies_today, robbery_successes_today, guard_duels_today, last_crime_date
            FROM casino_jail_records
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        robberies_today = int(row["robberies_today"] or 0) if row else 0
        robbery_successes_today = int(row["robbery_successes_today"] or 0) if row else 0
        guard_duels_today = int(row["guard_duels_today"] or 0) if row else 0
        if row and row["last_crime_date"] != today:
            robberies_today = 0
            robbery_successes_today = 0
            guard_duels_today = 0
        await db.execute(
            """
            UPDATE casino_jail_records
            SET robberies_today = ?, robbery_successes_today = ?, guard_duels_today = ?, last_crime_date = ?
            WHERE user_id = ?
            """,
            (robberies_today + 1, robbery_successes_today, guard_duels_today, today, user_id),
        )
        await db.commit()
        return robberies_today + 1


async def consume_daily_guard_duel_attempt(user_id, today):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute(
            """
            SELECT robberies_today, robbery_successes_today, guard_duels_today, last_crime_date
            FROM casino_jail_records
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        robberies_today = int(row["robberies_today"] or 0) if row else 0
        robbery_successes_today = int(row["robbery_successes_today"] or 0) if row else 0
        guard_duels_today = int(row["guard_duels_today"] or 0) if row else 0
        if row and row["last_crime_date"] != today:
            robberies_today = 0
            robbery_successes_today = 0
            guard_duels_today = 0
        await db.execute(
            """
            UPDATE casino_jail_records
            SET robberies_today = ?, robbery_successes_today = ?, guard_duels_today = ?, last_crime_date = ?
            WHERE user_id = ?
            """,
            (robberies_today, robbery_successes_today, guard_duels_today + 1, today, user_id),
        )
        await db.commit()
        return guard_duels_today + 1


async def apply_game_result(user_id, money_delta, win=False, loss=False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (money_delta, user_id))
        if win:
            await db.execute(
                "UPDATE casino_game_stats SET wins = wins + 1 WHERE user_id = ?",
                (user_id,),
            )
        if loss:
            await db.execute(
                "UPDATE casino_game_stats SET losses = losses + 1 WHERE user_id = ?",
                (user_id,),
            )
        await db.commit()


async def get_active_sentence_end(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.commit()
        cursor = await db.execute(
            "SELECT sentence_ends_at FROM casino_jail_records WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None or row["sentence_ends_at"] is None:
            return None
        ends_at = datetime.fromisoformat(row["sentence_ends_at"])
        if get_utc_now() >= ends_at:
            await db.execute(
                "UPDATE casino_jail_records SET sentence_ends_at = NULL WHERE user_id = ?",
                (user_id,),
            )
            await db.commit()
            return None
        return ends_at


async def send_user_to_jail(user_id, minutes):
    sentence_end = get_utc_now() + timedelta(minutes=minutes)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.execute(
            """
            UPDATE casino_jail_records
            SET sentence_ends_at = ?
            WHERE user_id = ?
            """,
            (sentence_end.isoformat(), user_id),
        )
        await db.execute(
            "UPDATE casino_game_stats SET jail_count = jail_count + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()
    return sentence_end


async def release_from_jail(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.execute(
            "UPDATE casino_jail_records SET sentence_ends_at = NULL WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def extend_jail_sentence(user_id, minutes):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute(
            "SELECT sentence_ends_at FROM casino_jail_records WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        base_time = get_utc_now()
        if row and row["sentence_ends_at"]:
            current_end = datetime.fromisoformat(row["sentence_ends_at"])
            if current_end > base_time:
                base_time = current_end
        new_end = base_time + timedelta(minutes=minutes)
        await db.execute(
            "UPDATE casino_jail_records SET sentence_ends_at = ? WHERE user_id = ?",
            (new_end.isoformat(), user_id),
        )
        await db.commit()
        return new_end


async def bribe_for_release(user_id, cost, today):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        user_row = await cursor.fetchone()
        if user_row is None:
            return False, "user_missing", None

        cursor = await db.execute(
            "SELECT bribes_today, last_bribe_date FROM casino_jail_records WHERE user_id = ?",
            (user_id,),
        )
        jail_row = await cursor.fetchone()
        bribes_today = int(jail_row["bribes_today"] or 0)
        if jail_row["last_bribe_date"] != today:
            bribes_today = 0

        wallet = int(user_row["money"] or 0)
        if wallet < cost:
            return False, "insufficient_wallet", wallet

        await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (cost, user_id))
        await db.execute(
            """
            UPDATE casino_jail_records
            SET sentence_ends_at = NULL, bribes_today = ?, last_bribe_date = ?
            WHERE user_id = ?
            """,
            (bribes_today + 1, today, user_id),
        )
        await db.commit()
        return True, "ok", bribes_today


async def transfer_money_between_users(from_user_id, to_user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (amount, from_user_id))
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, to_user_id))
        await db.commit()


async def apply_bank_robbery_success(user_id, loot, today=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        if today is not None:
            cursor = await db.execute(
                """
                SELECT robberies_today, robbery_successes_today, guard_duels_today, last_crime_date
                FROM casino_jail_records
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = await cursor.fetchone()
            robberies_today = int(row["robberies_today"] or 0) if row else 0
            robbery_successes_today = int(row["robbery_successes_today"] or 0) if row else 0
            guard_duels_today = int(row["guard_duels_today"] or 0) if row else 0
            if row and row["last_crime_date"] != today:
                robberies_today = 0
                robbery_successes_today = 0
                guard_duels_today = 0
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (loot, user_id))
        await db.execute(
            """
            UPDATE casino_crime_stats
            SET bank_rob_success_count = bank_rob_success_count + 1,
                robbery_loot_total = robbery_loot_total + ?
            WHERE user_id = ?
            """,
            (loot, user_id),
        )
        if today is not None:
            await db.execute(
                """
                UPDATE casino_jail_records
                SET robberies_today = ?, robbery_successes_today = ?, guard_duels_today = ?, last_crime_date = ?
                WHERE user_id = ?
                """,
                (robberies_today, robbery_successes_today + 1, guard_duels_today, today, user_id),
            )
        await db.execute(
            """
            UPDATE casino_bank_accounts
            SET checking_balance = CASE
                WHEN checking_balance <= 0 THEN 0
                ELSE CAST(checking_balance * 0.98 AS INTEGER)
            END
            """
        )
        await db.commit()


async def record_player_robbery_success(user_id, loot, today=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        if today is not None:
            cursor = await db.execute(
                """
                SELECT robberies_today, robbery_successes_today, guard_duels_today, last_crime_date
                FROM casino_jail_records
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = await cursor.fetchone()
            robberies_today = int(row["robberies_today"] or 0) if row else 0
            robbery_successes_today = int(row["robbery_successes_today"] or 0) if row else 0
            guard_duels_today = int(row["guard_duels_today"] or 0) if row else 0
            if row and row["last_crime_date"] != today:
                robberies_today = 0
                robbery_successes_today = 0
                guard_duels_today = 0
        await db.execute(
            """
            UPDATE casino_crime_stats
            SET player_rob_success_count = player_rob_success_count + 1,
                robbery_loot_total = robbery_loot_total + ?
            WHERE user_id = ?
            """,
            (loot, user_id),
        )
        if today is not None:
            await db.execute(
                """
                UPDATE casino_jail_records
                SET robberies_today = ?, robbery_successes_today = ?, guard_duels_today = ?, last_crime_date = ?
                WHERE user_id = ?
                """,
                (robberies_today, robbery_successes_today + 1, guard_duels_today, today, user_id),
            )
        await db.commit()


async def get_total_bank_pool():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                COALESCE(SUM(checking_balance), 0),
                COALESCE(SUM(savings_balance), 0)
            FROM casino_bank_accounts
            """
        )
        row = await cursor.fetchone()
        checking = int(row[0] or 0)
        savings = int(row[1] or 0)
        return checking + savings


async def get_active_buffs(user_id, now=None):
    now = now or get_utc_now()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT buff_type, expires_at
            FROM casino_buffs
            WHERE user_id = ? AND expires_at > ?
            ORDER BY expires_at ASC
            """,
            (user_id, now.isoformat()),
        )
        rows = await cursor.fetchall()
        return [(row["buff_type"], row["expires_at"]) for row in rows]


async def has_active_buff(user_id, buff_type, now=None):
    now = now or get_utc_now()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT 1
            FROM casino_buffs
            WHERE user_id = ? AND buff_type = ? AND expires_at > ?
            """,
            (user_id, buff_type, now.isoformat()),
        )
        return await cursor.fetchone() is not None


async def get_buff_bonus_multiplier(user_id, now=None):
    now = now or get_utc_now()
    bonus_multiplier = 1.0
    active_buffs = await get_active_buffs(user_id, now=now)
    for buff_type, _expires_at in active_buffs:
        if buff_type == "good_luck":
            bonus_multiplier += 0.05
        elif buff_type == "super_luck":
            bonus_multiplier += 0.15
        elif buff_type == "casino_focus":
            bonus_multiplier += 0.20
    return bonus_multiplier


async def get_shop_purchase_state(user_id, item_name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT purchase_count, last_purchase_date
            FROM casino_shop_logs
            WHERE user_id = ? AND item_name = ?
            """,
            (user_id, item_name),
        )
        row = await cursor.fetchone()
        if row is None:
            return 0, None
        return int(row["purchase_count"] or 0), row["last_purchase_date"]


async def get_gambling_profile(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)
        await db.commit()
        cursor = await db.execute(
            """
            SELECT bet_mode, custom_bet, last_bet, random_min_percent, random_max_percent
            FROM casino_gambling_profiles
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "bet_mode": row["bet_mode"] or "random",
            "custom_bet": int(row["custom_bet"] or 500),
            "last_bet": int(row["last_bet"] or 0),
            "random_min_percent": int(row["random_min_percent"] or 5),
            "random_max_percent": int(row["random_max_percent"] or 15),
        }


async def update_gambling_profile(
    user_id,
    *,
    bet_mode=None,
    custom_bet=None,
    last_bet=None,
    random_min_percent=None,
    random_max_percent=None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await _ensure_casino_rows(db, user_id)

        fields = []
        values = []
        if bet_mode is not None:
            fields.append("bet_mode = ?")
            values.append(bet_mode)
        if custom_bet is not None:
            fields.append("custom_bet = ?")
            values.append(custom_bet)
        if last_bet is not None:
            fields.append("last_bet = ?")
            values.append(last_bet)
        if random_min_percent is not None:
            fields.append("random_min_percent = ?")
            values.append(random_min_percent)
        if random_max_percent is not None:
            fields.append("random_max_percent = ?")
            values.append(random_max_percent)

        if fields:
            values.append(user_id)
            await db.execute(
                f"UPDATE casino_gambling_profiles SET {', '.join(fields)} WHERE user_id = ?",
                values,
            )
        await db.commit()


async def purchase_buff_item(user_id, item_name, price, buff_type, duration_hours, today, daily_limit):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        user_row = await cursor.fetchone()
        if user_row is None:
            return False, "user_missing", None

        wallet = int(user_row["money"] or 0)
        if wallet < price:
            return False, "insufficient_wallet", wallet

        cursor = await db.execute(
            """
            SELECT purchase_count, last_purchase_date
            FROM casino_shop_logs
            WHERE user_id = ? AND item_name = ?
            """,
            (user_id, item_name),
        )
        row = await cursor.fetchone()
        current_count = 0
        if row and row["last_purchase_date"] == today:
            current_count = int(row["purchase_count"] or 0)
        if current_count + 1 > daily_limit:
            return False, "daily_limit", max(0, daily_limit - current_count)

        now = get_utc_now()
        cursor = await db.execute(
            """
            SELECT expires_at
            FROM casino_buffs
            WHERE user_id = ? AND buff_type = ?
            """,
            (user_id, buff_type),
        )
        buff_row = await cursor.fetchone()
        start_time = now
        if buff_row and buff_row["expires_at"]:
            old_expire = datetime.fromisoformat(buff_row["expires_at"])
            if old_expire > now:
                start_time = old_expire

        final_expire = start_time + timedelta(hours=duration_hours)
        await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (price, user_id))
        await db.execute(
            """
            INSERT INTO casino_shop_logs (user_id, item_name, purchase_count, last_purchase_date)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, item_name) DO UPDATE
            SET purchase_count = CASE
                WHEN last_purchase_date = excluded.last_purchase_date THEN purchase_count + 1
                ELSE 1
            END,
            last_purchase_date = excluded.last_purchase_date
            """,
            (user_id, item_name, today),
        )
        await db.execute(
            """
            INSERT INTO casino_buffs (user_id, buff_type, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, buff_type) DO UPDATE SET expires_at = excluded.expires_at
            """,
            (user_id, buff_type, final_expire.isoformat()),
        )
        await db.commit()
        return True, "ok", final_expire


async def activate_or_extend_buff(user_id, buff_type, duration_hours):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = get_utc_now()
        cursor = await db.execute(
            """
            SELECT expires_at
            FROM casino_buffs
            WHERE user_id = ? AND buff_type = ?
            """,
            (user_id, buff_type),
        )
        buff_row = await cursor.fetchone()
        start_time = now
        if buff_row and buff_row["expires_at"]:
            old_expire = datetime.fromisoformat(buff_row["expires_at"])
            if old_expire > now:
                start_time = old_expire

        final_expire = start_time + timedelta(hours=duration_hours)
        await db.execute(
            """
            INSERT INTO casino_buffs (user_id, buff_type, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, buff_type) DO UPDATE SET expires_at = excluded.expires_at
            """,
            (user_id, buff_type, final_expire.isoformat()),
        )
        await db.commit()
        return final_expire


__all__ = [
    "DB_PATH",
    "apply_bank_robbery_success",
    "apply_game_result",
    "activate_or_extend_buff",
    "bribe_for_release",
    "deposit_to_account",
    "ensure_casino_user",
    "extend_jail_sentence",
    "get_active_sentence_end",
    "get_active_buffs",
    "get_bank_account",
    "get_bank_leaderboard",
    "get_buff_bonus_multiplier",
    "get_casino_stats",
    "get_daily_crime_counters",
    "get_gambling_profile",
    "get_shop_purchase_state",
    "get_total_bank_pool",
    "get_wallet_and_level",
    "has_active_buff",
    "purchase_buff_item",
    "consume_daily_guard_duel_attempt",
    "consume_daily_robbery_attempt",
    "record_player_robbery_success",
    "release_from_jail",
    "send_user_to_jail",
    "transfer_money_between_users",
    "update_gambling_profile",
    "withdraw_from_account",
]
