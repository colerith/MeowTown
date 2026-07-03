from __future__ import annotations

import logging
from datetime import datetime

import aiosqlite

from app.db.engine import DB_PATH
from app.features.economy.service import (
    ECONOMY_AUTO_GLOBAL_COOLDOWN_SECONDS,
    ECONOMY_AUTO_GLOBAL_OVER_CAP_TRIGGER,
    ECONOMY_AUTO_GLOBAL_PEAK_TRIGGER,
    ECONOMY_AUTO_GLOBAL_TOTAL_TRIGGER,
    ECONOMY_AUTO_USER_TRIGGER,
    ECONOMY_SOFT_CAP,
    revalue_amount,
)


MONEY_TABLE_COLUMNS = {
    "users": ("money",),
    "loans": ("loan_amount",),
    "casino_bank_accounts": ("checking_balance", "savings_balance"),
    "casino_gambling_profiles": ("custom_bet", "last_bet"),
    "casino_crime_stats": ("robbery_loot_total",),
    "farm_theft_stats": ("steal_income_total",),
    "daily_signins": ("last_reward",),
}
SQLITE_INT64_MAX = 9223372036854775807
logger = logging.getLogger("喵喵小镇")


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
        return await _get_economy_snapshot_with_db(db, limit=limit)


async def _get_economy_snapshot_with_db(db, limit=10):
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


async def _get_latest_rebase_log_with_db(db, *, trigger_kind: str | None = None):
    query = """
        SELECT
            executed_at,
            operator_user_id,
            trigger_kind,
            trigger_reason,
            target_user_id,
            changed_rows,
            total_before,
            total_after
        FROM economy_rebase_logs
    """
    params = []
    if trigger_kind:
        query += " WHERE trigger_kind = ?"
        params.append(trigger_kind)
    query += " ORDER BY id DESC LIMIT 1"
    cursor = await db.execute(query, params)
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "executed_at": row["executed_at"],
        "operator_user_id": row["operator_user_id"],
        "trigger_kind": row["trigger_kind"] or "manual",
        "trigger_reason": row["trigger_reason"],
        "target_user_id": row["target_user_id"],
        "changed_rows": int(row["changed_rows"] or 0),
        "total_before": _safe_numeric_to_int(row["total_before"]),
        "total_after": _safe_numeric_to_int(row["total_after"]),
    }


async def _apply_rebase_with_db(
    db,
    *,
    operator_user_id: int | None = None,
    trigger_kind: str = "manual",
    trigger_reason: str | None = None,
    target_user_id: int | None = None,
):
    changed_rows = 0
    total_before = 0
    total_after = 0

    for table_name, columns in MONEY_TABLE_COLUMNS.items():
        pk_cursor = await db.execute(f"PRAGMA table_info({table_name})")
        pk_rows = await pk_cursor.fetchall()
        pk_columns = [row["name"] for row in pk_rows if int(row["pk"] or 0) > 0]
        all_columns = {row["name"] for row in pk_rows}
        if not pk_columns:
            pk_columns = ["rowid"]

        select_columns = list(pk_columns) + list(columns)
        where_clause = ""
        params = []
        if target_user_id is not None and "user_id" in all_columns:
            where_clause = " WHERE user_id = ?"
            params.append(target_user_id)
        cursor = await db.execute(
            f"SELECT {', '.join(select_columns)} FROM {table_name}{where_clause}",
            params,
        )
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

            pk_where = " AND ".join(f"{pk_column} = ?" for pk_column in pk_columns)
            values.extend(row[pk_column] for pk_column in pk_columns)
            await db.execute(
                f"UPDATE {table_name} SET {', '.join(assignments)} WHERE {pk_where}",
                values,
            )
            changed_rows += 1

    await db.execute(
        """
        INSERT INTO economy_rebase_logs (
            executed_at, operator_user_id, trigger_kind, trigger_reason, target_user_id,
            changed_rows, total_before, total_after
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(timespec="seconds"),
            operator_user_id,
            trigger_kind,
            trigger_reason,
            target_user_id,
            changed_rows,
            _sqlite_log_value(total_before),
            _sqlite_log_value(total_after),
        ),
    )

    return {
        "trigger_kind": trigger_kind,
        "trigger_reason": trigger_reason,
        "target_user_id": target_user_id,
        "changed_rows": changed_rows,
        "total_before": total_before,
        "total_after": total_after,
    }


async def _maybe_apply_personal_rebase_with_db(db, user_id: int, source: str):
    cursor = await db.execute(
        """
        SELECT
            COALESCE(u.money, 0) AS money,
            COALESCE(b.checking_balance, 0) AS checking_balance,
            COALESCE(b.savings_balance, 0) AS savings_balance
        FROM users u
        LEFT JOIN casino_bank_accounts b ON b.user_id = u.user_id
        WHERE u.user_id = ?
        """,
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    largest_balance = max(
        _safe_numeric_to_int(row["money"]),
        _safe_numeric_to_int(row["checking_balance"]),
        _safe_numeric_to_int(row["savings_balance"]),
    )
    if largest_balance < ECONOMY_AUTO_USER_TRIGGER:
        return None

    result = await _apply_rebase_with_db(
        db,
        trigger_kind="auto_personal",
        trigger_reason=source,
        target_user_id=user_id,
    )
    if result["changed_rows"] <= 0:
        return None

    logger.warning(
        "💥 自动个人经济熔断已触发 | user_id=%s | source=%s | before=%s | after=%s",
        user_id,
        source,
        result["total_before"],
        result["total_after"],
    )
    return result


async def _maybe_apply_global_rebase_with_db(db, source: str):
    snapshot = await _get_economy_snapshot_with_db(db, limit=1)
    should_trigger = (
        snapshot["max_money"] >= ECONOMY_AUTO_GLOBAL_PEAK_TRIGGER
        or snapshot["total_money"] >= ECONOMY_AUTO_GLOBAL_TOTAL_TRIGGER
        or snapshot["over_soft_cap"] >= ECONOMY_AUTO_GLOBAL_OVER_CAP_TRIGGER
    )
    if not should_trigger:
        return None

    latest_global = await _get_latest_rebase_log_with_db(db, trigger_kind="auto_global")
    if latest_global is not None:
        last_run = datetime.fromisoformat(latest_global["executed_at"])
        elapsed = (datetime.utcnow() - last_run).total_seconds()
        if elapsed < ECONOMY_AUTO_GLOBAL_COOLDOWN_SECONDS:
            return None

    result = await _apply_rebase_with_db(
        db,
        trigger_kind="auto_global",
        trigger_reason=source,
    )
    if result["changed_rows"] <= 0:
        return None

    logger.warning(
        "🌐 自动全服经济熔断已触发 | source=%s | peak=%s | total=%s | over_soft_cap=%s | before=%s | after=%s",
        source,
        snapshot["max_money"],
        snapshot["total_money"],
        snapshot["over_soft_cap"],
        result["total_before"],
        result["total_after"],
    )
    return result


async def maybe_apply_auto_economy_guard_with_db(db, *, user_id: int | None = None, source: str = "unknown"):
    events = []
    if user_id is not None:
        personal_result = await _maybe_apply_personal_rebase_with_db(db, user_id, source)
        if personal_result is not None:
            events.append(personal_result)

    global_result = await _maybe_apply_global_rebase_with_db(db, source)
    if global_result is not None:
        events.append(global_result)
    return events


async def maybe_apply_global_economy_guard(source: str = "startup"):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        result = await _maybe_apply_global_rebase_with_db(db, source)
        await db.commit()
        return result


async def apply_economy_rebase(operator_user_id: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("BEGIN")
        result = await _apply_rebase_with_db(db, operator_user_id=operator_user_id)
        await db.commit()
        return result


async def get_latest_economy_rebase_log():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        return await _get_latest_rebase_log_with_db(db)


__all__ = [
    "apply_economy_rebase",
    "get_economy_snapshot",
    "get_latest_economy_rebase_log",
    "maybe_apply_auto_economy_guard_with_db",
    "maybe_apply_global_economy_guard",
]
