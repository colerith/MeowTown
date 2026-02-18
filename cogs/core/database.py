# core/database.py
import aiosqlite

DB_PATH = "./data/meowtown.db" # 数据库文件路径

async def get_db_pool() -> aiosqlite.Connection:
    """创建并返回数据库连接池"""
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    """初始化数据库，创建所有表"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 市民表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS citizens (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                species TEXT,
                pattern TEXT,
                money REAL DEFAULT 1000,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active_title TEXT
            )
        """)
        # 称号表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title_id TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES citizens (user_id)
            )
        """)
        # 物品表 (背包)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES citizens (user_id)
            )
        """)
        await db.commit()