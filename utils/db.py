# utils/db.py
import aiosqlite
import os
import time

DB_PATH = "./data/meowtown.db"

async def setup_db():
    """初始化数据库表结构"""
    if not os.path.exists("./data"):
        os.makedirs("./data")

    async with aiosqlite.connect(DB_PATH) as db:
        # 1. 用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                cat_name TEXT,
                cat_species TEXT,
                cat_pattern TEXT,
                money INTEGER DEFAULT 1000,
                status TEXT DEFAULT 'normal',
                active_title TEXT,
                cat_accessory TEXT
            )
        """)

        # 2. 农场表 (增加 is_notified)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                user_id INTEGER,
                plot_id INTEGER,
                plant_id TEXT,
                planted_at INTEGER,
                is_notified INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, plot_id)
            )
        """)

        # 3. 股市
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_id TEXT PRIMARY KEY,
                current_price REAL NOT NULL,
                last_change REAL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                user_id INTEGER,
                stock_id TEXT,
                quantity INTEGER,
                PRIMARY KEY (user_id, stock_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                user_id INTEGER PRIMARY KEY,
                loan_amount INTEGER
            )
        """)

        # 4. 大富翁
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monopoly_players (
                user_id INTEGER PRIMARY KEY,
                position INTEGER DEFAULT 0,
                status TEXT DEFAULT 'normal',
                jail_turns_left INTEGER DEFAULT 0,
                next_dice_fixed INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monopoly_properties (
                map_id INTEGER PRIMARY KEY,
                owner_id INTEGER,
                level INTEGER DEFAULT 0,
                effect TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monopoly_items (
                user_id INTEGER,
                item_name TEXT,
                count INTEGER,
                PRIMARY KEY (user_id, item_name)
            )
        """)

        # 5. 称号
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_titles (
                user_id INTEGER,
                title_id TEXT,
                obtained_at INTEGER,
                PRIMARY KEY (user_id, title_id)
            )
        """)

        # --- 自动迁移 ---
        try: await db.execute("ALTER TABLE users ADD COLUMN active_title TEXT")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN cat_accessory TEXT")
        except: pass
        try: await db.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'normal'")
        except: pass
        try: await db.execute("ALTER TABLE monopoly_players ADD COLUMN next_dice_fixed INTEGER DEFAULT 0")
        except: pass
        try: await db.execute("ALTER TABLE monopoly_properties ADD COLUMN effect TEXT")
        except: pass
        
        # 【新增】尝试添加农场通知字段
        try: await db.execute("ALTER TABLE farms ADD COLUMN is_notified INTEGER DEFAULT 0")
        except: pass

        await db.commit()

# --- 操作函数 ---

async def get_citizen(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_citizen(user_id, name, species, pattern, money):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users (user_id, cat_name, cat_species, cat_pattern, money, status) VALUES (?, ?, ?, ?, ?, 'normal')", (user_id, name, species, pattern, money))
        await db.commit()

async def update_citizen_look(user_id, species, pattern):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET cat_species = ?, cat_pattern = ? WHERE user_id = ?", (species, pattern, user_id))
        await db.commit()

async def update_money(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def set_user_status(user_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def equip_accessory(user_id, icon):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET cat_accessory = ? WHERE user_id = ?", (icon, user_id))
        await db.commit()

# --- 农场 ---
async def get_farm_state(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM farms WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                for i in range(4): await db.execute("INSERT INTO farms (user_id, plot_id) VALUES (?, ?)", (user_id, i))
                await db.commit()
                async with db.execute("SELECT * FROM farms WHERE user_id = ?", (user_id,)) as cursor: rows = await cursor.fetchall()
            return rows

async def plant_seed(user_id, plot_id, plant_id, current_time):
    async with aiosqlite.connect(DB_PATH) as db:
        # 种植时重置 notified 状态
        await db.execute(
            "UPDATE farms SET plant_id = ?, planted_at = ?, is_notified = 0 WHERE user_id = ? AND plot_id = ?",
            (plant_id, current_time, user_id, plot_id)
        )
        await db.commit()

async def clear_plot(user_id, plot_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE farms SET plant_id = NULL, planted_at = NULL, is_notified = 0 WHERE user_id = ? AND plot_id = ?", (user_id, plot_id))
        await db.commit()

async def add_farm_plot(user_id, plot_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO farms (user_id, plot_id) VALUES (?, ?)", (user_id, plot_id))
        await db.commit()

# 获取所有需要通知的农场数据
async def get_all_active_farms():
    async with aiosqlite.connect(DB_PATH) as db:
        # 获取所有已种植且未通知的行
        async with db.execute("SELECT user_id, plant_id, planted_at FROM farms WHERE plant_id IS NOT NULL AND is_notified = 0") as cursor:
            return await cursor.fetchall()

# 标记已通知
async def mark_farm_notified(user_id, plant_id):
    async with aiosqlite.connect(DB_PATH) as db:
        # 这里简化处理：将该用户下该种植物的所有地块都标记已通知，防止刷屏
        await db.execute("UPDATE farms SET is_notified = 1 WHERE user_id = ? AND plant_id = ?", (user_id, plant_id))
        await db.commit()

# --- 道具 ---
async def add_item(user_id, item_name, count=1):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO monopoly_items (user_id, item_name, count) VALUES (?, ?, ?) ON CONFLICT(user_id, item_name) DO UPDATE SET count = count + excluded.count", (user_id, item_name, count))
        await db.commit()

async def use_item_from_db(user_id, item_name):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT count FROM monopoly_items WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        row = await cursor.fetchone()
        if not row or row[0] < 1: return False 
        new_count = row[0] - 1
        if new_count == 0: await db.execute("DELETE FROM monopoly_items WHERE user_id = ? AND item_name = ?", (user_id, item_name))
        else: await db.execute("UPDATE monopoly_items SET count = ? WHERE user_id = ? AND item_name = ?", (new_count, user_id, item_name))
        await db.commit()
        return True

async def get_items(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT item_name, count FROM monopoly_items WHERE user_id = ?", (user_id,))
        return await cursor.fetchall()

# --- 称号 ---
async def unlock_title(user_id, title_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO user_titles (user_id, title_id, obtained_at) VALUES (?, ?, ?)", (user_id, title_id, int(time.time())))
        await db.commit()

async def check_title_owned(user_id, title_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM user_titles WHERE user_id = ? AND title_id = ?", (user_id, title_id))
        return await cursor.fetchone() is not None

async def equip_user_title(user_id, title_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET active_title = ? WHERE user_id = ?", (title_name, user_id))
        await db.commit()

async def get_user_titles(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT title_id FROM user_titles WHERE user_id = ?", (user_id,))
        return [row[0] for row in await cursor.fetchall()]