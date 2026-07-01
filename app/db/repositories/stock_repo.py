import aiosqlite

from app.db.engine import DB_PATH


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

        await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_value, user_id))
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

        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (total_value, user_id))
        await db.commit()
        return True, owned_quantity


async def get_loan_amount(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0.0


async def borrow_money(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
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
        await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (amount, user_id))
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


__all__ = [
    "borrow_money",
    "buy_stock",
    "get_loan_amount",
    "get_portfolio_positions",
    "get_portfolio_with_prices",
    "get_stock_price",
    "initialize_stocks",
    "list_market_stocks",
    "repay_loan",
    "sell_stock",
    "update_stock_quote",
]
