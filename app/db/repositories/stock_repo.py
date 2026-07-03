import datetime

import aiosqlite

from app.db.engine import DB_PATH
from app.db.repositories.user_repo import apply_money_delta_with_db


async def list_market_stocks():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT stock_id, current_price, last_change FROM stocks ORDER BY stock_id"
        )
        return await cursor.fetchall()


async def get_stock_price(stock_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (stock_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def buy_stock(user_id, stock_id, quantity, unit_price):
    total_value = round(unit_price * quantity, 2)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        user_money = row[0] if row else 0.0
        if user_money < total_value:
            return False, user_money

        await apply_money_delta_with_db(db, user_id, -total_value, economy_mode="direct")
        await db.execute(
            """
            INSERT INTO portfolios (user_id, stock_id, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, stock_id) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (user_id, stock_id, quantity),
        )
        await db.commit()
        return True, user_money


async def sell_stock(user_id, stock_id, quantity, unit_price):
    total_value = round(unit_price * quantity, 2)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT quantity FROM portfolios WHERE user_id = ? AND stock_id = ?",
            (user_id, stock_id),
        )
        row = await cursor.fetchone()
        owned_quantity = row[0] if row else 0
        if owned_quantity < quantity:
            return False, owned_quantity

        new_quantity = owned_quantity - quantity
        if new_quantity == 0:
            await db.execute("DELETE FROM portfolios WHERE user_id = ? AND stock_id = ?", (user_id, stock_id))
        else:
            await db.execute(
                "UPDATE portfolios SET quantity = ? WHERE user_id = ? AND stock_id = ?",
                (new_quantity, user_id, stock_id),
            )

        summary = await apply_money_delta_with_db(db, user_id, total_value, economy_mode="gameplay")
        await db.commit()
        return True, owned_quantity, summary


async def get_loan_amount(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0.0


async def borrow_money(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await apply_money_delta_with_db(db, user_id, amount, economy_mode="direct")
        await db.execute(
            """
            INSERT INTO loans (user_id, loan_amount) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET loan_amount = loan_amount + excluded.loan_amount
            """,
            (user_id, amount),
        )
        await db.commit()


async def repay_loan(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await apply_money_delta_with_db(db, user_id, -amount, economy_mode="direct")
        await db.execute("UPDATE loans SET loan_amount = loan_amount - ? WHERE user_id = ?", (amount, user_id))
        await db.commit()


async def get_portfolio_positions(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT stock_id, quantity FROM portfolios WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()


async def get_portfolio_with_prices(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT p.stock_id, p.quantity, COALESCE(s.current_price, 0)
            FROM portfolios p
            LEFT JOIN stocks s ON p.stock_id = s.stock_id
            WHERE p.user_id = ?
            ORDER BY p.stock_id
            """,
            (user_id,),
        )
        return await cursor.fetchall()


async def initialize_stocks(stock_config):
    async with aiosqlite.connect(DB_PATH) as db:
        for stock_id, data in stock_config.items():
            cursor = await db.execute("SELECT 1 FROM stocks WHERE stock_id = ?", (stock_id,))
            if not await cursor.fetchone():
                await db.execute(
                    "INSERT INTO stocks (stock_id, current_price) VALUES (?, ?)",
                    (stock_id, data["base_price"]),
                )
        await db.commit()


async def update_stock_quote(stock_id, new_price, price_diff):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE stocks SET current_price = ?, last_change = ? WHERE stock_id = ?",
            (new_price, price_diff, stock_id),
        )
        await db.commit()


async def reset_stock_market(stock_config):
    async with aiosqlite.connect(DB_PATH) as db:
        for stock_id, data in stock_config.items():
            await db.execute(
                """
                INSERT INTO stocks (stock_id, current_price, last_change)
                VALUES (?, ?, 0)
                ON CONFLICT(stock_id) DO UPDATE SET
                    current_price = excluded.current_price,
                    last_change = 0
                """,
                (stock_id, data["base_price"]),
            )
        await db.commit()


async def grant_stock_shares(user_id, stock_id, quantity):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO portfolios (user_id, stock_id, quantity) VALUES (?, ?, ?)
            ON CONFLICT(user_id, stock_id) DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (user_id, stock_id, quantity),
        )
        await db.commit()


async def has_claimed_stock_compensation(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM stock_compensation_claims WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchone() is not None


async def claim_stock_compensation(user_id, stock_ids, quantity_per_stock):
    claimed_at = datetime.datetime.utcnow().isoformat(timespec="seconds")
    serialized_stock_ids = ",".join(stock_ids)

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN")
            cursor = await db.execute(
                "SELECT 1 FROM stock_compensation_claims WHERE user_id = ?",
                (user_id,),
            )
            if await cursor.fetchone():
                await db.rollback()
                return False

            await db.execute(
                """
                INSERT INTO stock_compensation_claims (user_id, stock_ids, quantity_per_stock, claimed_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, serialized_stock_ids, quantity_per_stock, claimed_at),
            )

            for stock_id in stock_ids:
                await db.execute(
                    """
                    INSERT INTO portfolios (user_id, stock_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, stock_id) DO UPDATE SET quantity = quantity + excluded.quantity
                    """,
                    (user_id, stock_id, quantity_per_stock),
                )

            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise


__all__ = [
    "borrow_money",
    "buy_stock",
    "claim_stock_compensation",
    "grant_stock_shares",
    "get_loan_amount",
    "get_portfolio_positions",
    "get_portfolio_with_prices",
    "get_stock_price",
    "has_claimed_stock_compensation",
    "initialize_stocks",
    "list_market_stocks",
    "repay_loan",
    "reset_stock_market",
    "sell_stock",
    "update_stock_quote",
]
