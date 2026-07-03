from __future__ import annotations

from datetime import datetime

import aiosqlite

from app.db.engine import DB_PATH
from app.db.repositories.user_repo import SQLITE_INT64_MAX
from app.features.economy.service import ECONOMY_SOFT_CAP, revalue_amount


MONEY_TABLE_COLUMNS = {
    "users": ("money",),
    "loans": ("loan_amount",),
    "casino_bank_accounts": ("checking_balance", "savings_balance"),
    "casino_gambling_profiles": ("custom_bet", "last_bet"),
    "casino_crime_stats": ("robbery_loot_total",),
    "farm_theft_stats": ("steal_income_total",),
    "daily_signins": ("last_reward",),
}


def _safe_numeric_to_int(value) -> int:
    if value is None:
        return 0
    return int(round(float(value)))


def _sqlite_log_value(value):
    safe_value = _safe_numeric_to_int(value)
    if abs(safe_value) > SQLITE_INT64_MAX:
        return str(safe_value)
    return safe_value


async def get_economy_snapshot(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                user_id,
                cat_name,
                COALESCE(money, 0) AS money
            FROM users
            ORDER BY money DESC, user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        top_users = await cursor.fetchall()

        cursor = await db.execute(
            """
            SELECT
                user_id,
                cat_name,
                COALESCE(money, 0) AS money
            FROM users
            ORDER BY user_id ASC
            """
        )
        all_users = await cursor.fetchall()

        max_money = 0
        total_money = 0
        over_soft_cap = 0
        for row in all_users:
            money_value = _safe_numeric_to_int(row["money"])
            if money_value > max_money:
                max_money = money_value
            total_money += money_value
            if money_value > ECONOMY_SOFT_CAP:
                over_soft_cap += 1

        return {
            "user_count": len(all_users),
            "max_money": max_money,
            "total_money": total_money,
            "over_soft_cap": over_soft_cap,
            "top_users": [
                (
                    int(row["user_id"]),
                    row["cat_name"],
                    _safe_numeric_to_int(row["money"]),
                    revalue_amount(row["money"] or 0),
                )
                for row in top_users
            ],
        }


async def apply_economy_rebase(operator_user_id: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN")

        changed_rows = 0
        total_before = 0
        total_after = 0

        for table_name, columns in MONEY_TABLE_COLUMNS.items():
            pk_cursor = await db.execute(f"PRAGMA table_info({table_name})")
            pk_rows = await pk_cursor.fetchall()
            pk_columns = [row["name"] for row in pk_rows if int(row["pk"] or 0) > 0]
            if not pk_columns:
                pk_columns = ["rowid"]

            select_columns = list(pk_columns) + list(columns)
            cursor = await db.execute(f"SELECT {', '.join(select_columns)} FROM {table_name}")
            rows = await cursor.fetchall()

            for row in rows:
                assignments = []
                values = []
                row_changed = False

                for column in columns:
                    before_value = row[column] or 0
                    before_int = _safe_numeric_to_int(before_value)
                    after_int = revalue_amount(before_value)
                    total_before += before_int
                    total_after += after_int
                    if before_int != after_int:
                        assignments.append(f"{column} = ?")
                        values.append(after_int)
                        row_changed = True

                if not row_changed:
                    continue

                where_clause = " AND ".join(f"{pk_column} = ?" for pk_column in pk_columns)
                values.extend(row[pk_column] for pk_column in pk_columns)
                await db.execute(
                    f"UPDATE {table_name} SET {', '.join(assignments)} WHERE {where_clause}",
                    values,
                )
                changed_rows += 1

        await db.execute(
            """
            INSERT INTO economy_rebase_logs (executed_at, operator_user_id, changed_rows, total_before, total_after)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(timespec="seconds"),
                operator_user_id,
                changed_rows,
                _sqlite_log_value(total_before),
                _sqlite_log_value(total_after),
            ),
        )
        await db.commit()

        return {
            "changed_rows": changed_rows,
            "total_before": total_before,
            "total_after": total_after,
        }


async def get_latest_economy_rebase_log():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT executed_at, operator_user_id, changed_rows, total_before, total_after
            FROM economy_rebase_logs
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "executed_at": row["executed_at"],
            "operator_user_id": row["operator_user_id"],
            "changed_rows": int(row["changed_rows"] or 0),
            "total_before": _safe_numeric_to_int(row["total_before"]),
            "total_after": _safe_numeric_to_int(row["total_after"]),
        }


__all__ = [
    "apply_economy_rebase",
    "get_economy_snapshot",
    "get_latest_economy_rebase_log",
]
