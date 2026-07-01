import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.engine import setup_db
from app.db.repositories.stock_repo import reset_stock_market
from app.shared.data.stock_data import STOCKS


async def main():
    await setup_db()
    await reset_stock_market(STOCKS)
    print("Stock market data has been reset to base prices.")


if __name__ == "__main__":
    asyncio.run(main())
