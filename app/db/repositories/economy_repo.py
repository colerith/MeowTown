from __future__ import annotations

from datetime import datetime

import aiosqlite

from app.db.engine import DB_PATH
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
                COUNT(*) AS user_count,
                COALESCE(MAX(money), 0) AS max_money,
                COALESCE(SUM(money), 0) AS total_money,
                COALESCE(SUM(CASE WHEN money > ? THEN 1 ELSE 0 END), 0) AS over_soft_cap
            FROM users
            """
            ,
            (ECONOMY_SOFT_CAP,),
        )
        totals = await cursor.fetchone()

        return {
            "user_count": int(totals["user_count"] or 0),
            "max_money": int(round(float(totals["max_money"] or 0))),
            "total_money": int(round(float(totals["total_money"] or 0))),
            "over_soft_cap": int(totals["over_soft_cap"] or 0),
            "top_users": [
                (
                    int(row["user_id"]),
                    row["cat_name"],
                    int(round(float(row["money"] or 0))),
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
                    before_int = int(round(float(before_value)))
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
                total_before,
                total_after,
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
            "total_before": int(row["total_before"] or 0),
            "total_after": int(row["total_after"] or 0),
        }


__all__ = [
    "apply_economy_rebase",
    "get_economy_snapshot",
    "get_latest_economy_rebase_log",
]
