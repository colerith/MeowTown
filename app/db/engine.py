import os

import aiosqlite


DB_PATH = "./data/meowtown.db"


async def setup_db():
	if not os.path.exists("./data"):
		os.makedirs("./data")

	async with aiosqlite.connect(DB_PATH) as db:
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS users (
				user_id INTEGER PRIMARY KEY,
				cat_name TEXT,
				cat_species TEXT,
				cat_pattern TEXT,
				money INTEGER DEFAULT 1000,
				status TEXT DEFAULT 'normal',
				active_title TEXT,
				cat_accessory TEXT,
				citizen_level INTEGER DEFAULT 1,
				level_score INTEGER DEFAULT 0
			)
			"""
		)

		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS farms (
				user_id INTEGER,
				plot_id INTEGER,
				plant_id TEXT,
				planted_at INTEGER,
				is_notified INTEGER DEFAULT 0,
				PRIMARY KEY (user_id, plot_id)
			)
			"""
		)

		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS stocks (
				stock_id TEXT PRIMARY KEY,
				current_price REAL NOT NULL,
				last_change REAL DEFAULT 0
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS portfolios (
				user_id INTEGER,
				stock_id TEXT,
				quantity INTEGER,
				PRIMARY KEY (user_id, stock_id)
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS loans (
				user_id INTEGER PRIMARY KEY,
				loan_amount INTEGER
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS farm_guards (
				user_id INTEGER PRIMARY KEY,
				guard_type TEXT NOT NULL,
				expires_at INTEGER NOT NULL,
				expired_notice_sent INTEGER DEFAULT 0
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS daily_signins (
				user_id INTEGER PRIMARY KEY,
				last_signin_date TEXT NOT NULL,
				total_signin_count INTEGER DEFAULT 0,
				last_reward INTEGER DEFAULT 0,
				updated_at TEXT NOT NULL
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS stock_compensation_claims (
				user_id INTEGER PRIMARY KEY,
				stock_ids TEXT NOT NULL,
				quantity_per_stock INTEGER NOT NULL,
				claimed_at TEXT NOT NULL
			)
			"""
		)

		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS monopoly_players (
				user_id INTEGER PRIMARY KEY,
				position INTEGER DEFAULT 0,
				status TEXT DEFAULT 'normal',
				jail_turns_left INTEGER DEFAULT 0,
				next_dice_fixed INTEGER DEFAULT 0
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS monopoly_properties (
				map_id INTEGER PRIMARY KEY,
				owner_id INTEGER,
				level INTEGER DEFAULT 0,
				effect TEXT,
				purchase_price REAL DEFAULT 0,
				maintenance_due_at INTEGER DEFAULT 0,
				maintenance_notice_sent INTEGER DEFAULT 0
			)
			"""
		)
		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS monopoly_items (
				user_id INTEGER,
				item_name TEXT,
				count INTEGER,
				PRIMARY KEY (user_id, item_name)
			)
			"""
		)

		await db.execute(
			"""
			CREATE TABLE IF NOT EXISTS user_titles (
				user_id INTEGER,
				title_id TEXT,
				obtained_at INTEGER,
				PRIMARY KEY (user_id, title_id)
			)
			"""
		)

		try:
			await db.execute("ALTER TABLE users ADD COLUMN active_title TEXT")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE users ADD COLUMN cat_accessory TEXT")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'normal'")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE users ADD COLUMN citizen_level INTEGER DEFAULT 1")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE users ADD COLUMN level_score INTEGER DEFAULT 0")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE monopoly_players ADD COLUMN next_dice_fixed INTEGER DEFAULT 0")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE monopoly_players ADD COLUMN bad_luck_count INTEGER DEFAULT 0")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE monopoly_properties ADD COLUMN effect TEXT")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE monopoly_properties ADD COLUMN purchase_price REAL DEFAULT 0")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE monopoly_properties ADD COLUMN maintenance_due_at INTEGER DEFAULT 0")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE monopoly_properties ADD COLUMN maintenance_notice_sent INTEGER DEFAULT 0")
		except Exception:
			pass
		await db.execute(
			"""
			UPDATE monopoly_properties
			SET maintenance_due_at = CAST(strftime('%s','now') AS INTEGER) + 604800
			WHERE owner_id IS NOT NULL AND (maintenance_due_at IS NULL OR maintenance_due_at <= 0)
			"""
		)
		try:
			await db.execute("ALTER TABLE farms ADD COLUMN is_notified INTEGER DEFAULT 0")
		except Exception:
			pass
		try:
			await db.execute("ALTER TABLE farm_guards ADD COLUMN expired_notice_sent INTEGER DEFAULT 0")
		except Exception:
			pass

		await db.commit()


__all__ = ["DB_PATH", "setup_db"]

