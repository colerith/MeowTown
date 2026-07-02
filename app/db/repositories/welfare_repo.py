import datetime
import json

import aiosqlite

from app.db.engine import DB_PATH


async def upsert_welfare_message(
    message_id,
    channel_id,
    title,
    body,
    mention_enabled,
    mention_content,
    role_rewards,
    money_reward,
    stock_rewards,
):
    updated_at = datetime.datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO welfare_messages (
                message_id, channel_id, title, body,
                mention_enabled, mention_content,
                role_rewards_json, money_reward_json, stock_rewards_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                title = excluded.title,
                body = excluded.body,
                mention_enabled = excluded.mention_enabled,
                mention_content = excluded.mention_content,
                role_rewards_json = excluded.role_rewards_json,
                money_reward_json = excluded.money_reward_json,
                stock_rewards_json = excluded.stock_rewards_json,
                updated_at = excluded.updated_at
            """,
            (
                message_id,
                channel_id,
                title,
                body,
                1 if mention_enabled else 0,
                mention_content,
                json.dumps(role_rewards, ensure_ascii=False),
                json.dumps(money_reward, ensure_ascii=False),
                json.dumps(stock_rewards, ensure_ascii=False),
                updated_at,
            ),
        )
        await db.commit()


async def get_welfare_message(message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT
                message_id, channel_id, title, body,
                mention_enabled, mention_content,
                role_rewards_json, money_reward_json, stock_rewards_json,
                updated_at
            FROM welfare_messages
            WHERE message_id = ?
            """,
            (message_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "message_id": row[0],
            "channel_id": row[1],
            "title": row[2],
            "body": row[3],
            "mention_enabled": bool(row[4]),
            "mention_content": row[5] or "",
            "role_rewards": json.loads(row[6] or "[]"),
            "money_reward": json.loads(row[7] or "{}"),
            "stock_rewards": json.loads(row[8] or "[]"),
            "updated_at": row[9],
        }


async def begin_welfare_claim(message_id, user_id):
    claimed_at = datetime.datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """
                INSERT INTO welfare_claims (message_id, user_id, payload_json, claimed_at, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (message_id, user_id, "{}", claimed_at),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def finish_welfare_claim(message_id, user_id, payload):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE welfare_claims
            SET payload_json = ?, status = 'claimed', role_notice_sent = 0
            WHERE message_id = ? AND user_id = ?
            """,
            (json.dumps(payload, ensure_ascii=False), message_id, user_id),
        )
        await db.commit()


async def cancel_welfare_claim(message_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM welfare_claims WHERE message_id = ? AND user_id = ? AND status = 'pending'",
            (message_id, user_id),
        )
        await db.commit()


async def has_claimed_welfare(message_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT status FROM welfare_claims WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def count_claimed_welfare_users(message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM welfare_claims WHERE message_id = ? AND status = 'claimed'",
            (message_id,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0


async def get_pending_role_notice_claims():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT message_id, user_id, payload_json, claimed_at
            FROM welfare_claims
            WHERE status = 'claimed' AND role_notice_sent = 0
            ORDER BY claimed_at ASC
            """
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            payload = json.loads(row[2] or "{}")
            role_ids = payload.get("roles") or []
            if not role_ids:
                continue
            results.append(
                {
                    "message_id": row[0],
                    "user_id": row[1],
                    "payload": payload,
                    "claimed_at": row[3],
                }
            )
        return results


async def mark_role_notice_sent(message_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE welfare_claims
            SET role_notice_sent = 1
            WHERE message_id = ? AND user_id = ?
            """,
            (message_id, user_id),
        )
        await db.commit()


__all__ = [
    "begin_welfare_claim",
    "cancel_welfare_claim",
    "finish_welfare_claim",
    "get_welfare_message",
    "count_claimed_welfare_users",
    "get_pending_role_notice_claims",
    "has_claimed_welfare",
    "mark_role_notice_sent",
    "upsert_welfare_message",
]
