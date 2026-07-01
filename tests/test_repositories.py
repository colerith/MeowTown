import asyncio
import os
import tempfile
import unittest

import aiosqlite

from app.db import engine
from app.db.repositories import (
    daily_repo,
    farm_repo,
    inventory_repo,
    monopoly_repo,
    ranking_repo,
    stock_repo,
    title_repo,
    user_repo,
)
from app.features.profile import repository as profile_repository


PATCHED_MODULES = [
    engine,
    daily_repo,
    farm_repo,
    inventory_repo,
    monopoly_repo,
    ranking_repo,
    stock_repo,
    title_repo,
    user_repo,
]


class RepositoryIntegrationTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        self.original_paths = {}
        for module in PATCHED_MODULES:
            self.original_paths[module] = module.DB_PATH
            module.DB_PATH = self.db_path

        await engine.setup_db()

    async def asyncTearDown(self):
        for module, original_path in self.original_paths.items():
            module.DB_PATH = original_path

        if os.path.exists(self.db_path):
            for _ in range(5):
                try:
                    os.remove(self.db_path)
                    break
                except PermissionError:
                    await asyncio.sleep(0.05)

    async def create_user(self, user_id, money=1000, name="Tester"):
        await user_repo.create_citizen(user_id, name, "橘猫", "虎斑", money)


class UserRepositoryTests(RepositoryIntegrationTestCase):
    async def test_user_repo_updates_profile_and_money(self):
        await self.create_user(1001, money=1500, name="Mimi")

        await user_repo.update_citizen_name(1001, "Momo")
        await user_repo.update_citizen_look(1001, "布偶猫", "奶油色")
        await user_repo.update_money(1001, 250.5)
        await user_repo.set_user_status(1001, "busy")
        await user_repo.equip_accessory(1001, "🎀")

        citizen = await user_repo.get_citizen(1001)
        self.assertEqual(citizen[1], "Momo")
        self.assertEqual(citizen[2], "布偶猫")
        self.assertEqual(citizen[3], "奶油色")
        self.assertAlmostEqual(citizen[4], 1750.5)
        self.assertEqual(citizen[5], "busy")
        self.assertEqual(citizen[7], "🎀")
        self.assertEqual(await user_repo.get_equipped_accessory(1001), "🎀")
        self.assertAlmostEqual(await user_repo.get_user_money(1001), 1750.5)

    async def test_user_repo_lists_registered_user_ids(self):
        await self.create_user(1002, name="A")
        await self.create_user(1003, name="B")

        self.assertEqual(await user_repo.list_registered_user_ids(), [1002, 1003])


class FarmRepositoryTests(RepositoryIntegrationTestCase):
    async def test_farm_repo_initializes_and_updates_plots(self):
        await self.create_user(1101, money=2000, name="Farmer")

        rows = await farm_repo.get_farm_state(1101)
        self.assertEqual(len(rows), 4)
        self.assertEqual([row[1] for row in rows], [0, 1, 2, 3])
        self.assertTrue(all(row[2] is None for row in rows))

        await farm_repo.plant_seed(1101, 1, "corn", 1000)
        rows = await farm_repo.get_farm_state(1101)
        plot = next(row for row in rows if row[1] == 1)
        self.assertEqual(plot[2], "corn")
        self.assertEqual(plot[3], 1000)

        await farm_repo.accelerate_farm_growth(1101, 300)
        rows = await farm_repo.get_farm_state(1101)
        plot = next(row for row in rows if row[1] == 1)
        self.assertEqual(plot[3], 700)

        active = await farm_repo.get_all_active_farms()
        self.assertEqual(active, [(1101, "corn", 700)])

        await farm_repo.mark_farm_notified(1101, "corn")
        self.assertEqual(await farm_repo.get_all_active_farms(), [])

        await farm_repo.clear_plot(1101, 1)
        rows = await farm_repo.get_farm_state(1101)
        plot = next(row for row in rows if row[1] == 1)
        self.assertIsNone(plot[2])
        self.assertIsNone(plot[3])

    async def test_farm_repo_can_expand_plot_count(self):
        await self.create_user(1102, money=2000, name="Expand")
        await farm_repo.get_farm_state(1102)
        await farm_repo.add_farm_plot(1102, 4)

        rows = await farm_repo.get_farm_state(1102)
        self.assertEqual(len(rows), 5)
        self.assertEqual(sorted(row[1] for row in rows), [0, 1, 2, 3, 4])

    async def test_farm_repo_tracks_farming_users_and_guards(self):
        await self.create_user(1103, money=2000, name="Guarded")
        await self.create_user(1104, money=2000, name="Other")
        await farm_repo.get_farm_state(1103)
        await farm_repo.get_farm_state(1104)
        await farm_repo.plant_seed(1103, 0, "corn", 1000)
        await farm_repo.plant_seed(1104, 0, "wheat", 1000)

        self.assertEqual(await farm_repo.get_all_farming_users(), [1103, 1104])
        self.assertEqual(await farm_repo.get_all_farming_users(exclude_user_id=1103), [1104])

        await farm_repo.set_farm_guard(1103, "dog", 5000)
        self.assertEqual(await farm_repo.get_farm_guard(1103, current_time=1000), ("dog", 5000))
        self.assertIsNone(await farm_repo.get_farm_guard(1103, current_time=5000))
        self.assertEqual(await farm_repo.get_expired_farm_guards(5000), [(1103, "dog", 5000)])
        await farm_repo.mark_farm_guard_notice_sent(1103)
        self.assertEqual(await farm_repo.get_expired_farm_guards(5000), [])
        await farm_repo.remove_farm_guard(1103)
        self.assertIsNone(await farm_repo.get_farm_guard(1103))


class DailyRepositoryTests(RepositoryIntegrationTestCase):
    async def test_daily_repo_records_and_counts_signins(self):
        await self.create_user(1201, name="Daily")

        self.assertIsNone(await daily_repo.get_daily_signin(1201))
        await daily_repo.record_daily_signin(1201, "2026-07-01", 8888)
        row = await daily_repo.get_daily_signin(1201)
        self.assertEqual(row[0], 1201)
        self.assertEqual(row[1], "2026-07-01")
        self.assertEqual(row[2], 1)
        self.assertEqual(row[3], 8888)
        self.assertEqual(await daily_repo.count_daily_signins_by_date("2026-07-01"), 1)

        await daily_repo.record_daily_signin(1201, "2026-07-02", 9999)
        row = await daily_repo.get_daily_signin(1201)
        self.assertEqual(row[1], "2026-07-02")
        self.assertEqual(row[2], 2)
        self.assertEqual(row[3], 9999)


class StockRepositoryTests(RepositoryIntegrationTestCase):
    async def test_stock_repo_buy_sell_and_loans(self):
        await self.create_user(2001, money=5000, name="Trader")
        await stock_repo.initialize_stocks(
            {
                "FISH": {"base_price": 10},
                "BOX": {"base_price": 20},
            }
        )

        self.assertEqual(await stock_repo.get_stock_price("FISH"), 10)

        success, balance = await stock_repo.buy_stock(2001, "FISH", 100, 10)
        self.assertTrue(success)
        self.assertEqual(balance, 5000)
        self.assertAlmostEqual(await user_repo.get_user_money(2001), 4000)
        self.assertEqual(await stock_repo.get_portfolio_positions(2001), [("FISH", 100)])

        success, owned_quantity = await stock_repo.sell_stock(2001, "FISH", 40, 12.5)
        self.assertTrue(success)
        self.assertEqual(owned_quantity, 100)
        self.assertAlmostEqual(await user_repo.get_user_money(2001), 4500)
        self.assertEqual(await stock_repo.get_portfolio_positions(2001), [("FISH", 60)])

        await stock_repo.borrow_money(2001, 800)
        self.assertAlmostEqual(await user_repo.get_user_money(2001), 5300)
        self.assertAlmostEqual(await stock_repo.get_loan_amount(2001), 800)

        await stock_repo.repay_loan(2001, 300)
        self.assertAlmostEqual(await user_repo.get_user_money(2001), 5000)
        self.assertAlmostEqual(await stock_repo.get_loan_amount(2001), 500)

    async def test_stock_repo_updates_quotes_and_portfolio_snapshot(self):
        await self.create_user(2002, money=3000, name="Snapshot")
        await stock_repo.initialize_stocks({"TOY": {"base_price": 15}})
        await stock_repo.buy_stock(2002, "TOY", 10, 15)
        await stock_repo.update_stock_quote("TOY", 18, 3)

        market_rows = await stock_repo.list_market_stocks()
        self.assertEqual(market_rows, [("TOY", 18.0, 3.0)])

        portfolio = await stock_repo.get_portfolio_with_prices(2002)
        self.assertEqual(portfolio, [("TOY", 10, 18.0)])

    async def test_stock_repo_can_reset_market_and_claim_compensation_once(self):
        await self.create_user(2003, money=3000, name="Comp")
        await stock_repo.initialize_stocks({"FISH": {"base_price": 50}, "BOX": {"base_price": 80}})
        await stock_repo.update_stock_quote("FISH", 999, 949)

        await stock_repo.reset_stock_market({"FISH": {"base_price": 50}, "BOX": {"base_price": 80}})
        self.assertEqual(await stock_repo.list_market_stocks(), [("BOX", 80.0, 0.0), ("FISH", 50.0, 0.0)])

        self.assertFalse(await stock_repo.has_claimed_stock_compensation(2003))
        self.assertTrue(await stock_repo.claim_stock_compensation(2003, ["FISH", "BOX"], 100))
        self.assertTrue(await stock_repo.has_claimed_stock_compensation(2003))
        self.assertFalse(await stock_repo.claim_stock_compensation(2003, ["FISH", "BOX"], 100))
        self.assertEqual(await stock_repo.get_portfolio_positions(2003), [("BOX", 100), ("FISH", 100)])


class InventoryRepositoryTests(RepositoryIntegrationTestCase):
    async def test_inventory_repo_tracks_and_consumes_items(self):
        await inventory_repo.add_item(2101, "roadblock", 2)
        await inventory_repo.add_item(2101, "roadblock", 1)
        await inventory_repo.add_item(2101, "remote_dice", 1)

        items = sorted(await inventory_repo.get_items(2101))
        self.assertEqual(items, [("remote_dice", 1), ("roadblock", 3)])

        self.assertTrue(await inventory_repo.use_item_from_db(2101, "roadblock"))
        self.assertEqual(sorted(await inventory_repo.get_items(2101)), [("remote_dice", 1), ("roadblock", 2)])

        self.assertTrue(await inventory_repo.use_item_from_db(2101, "remote_dice"))
        self.assertEqual(await inventory_repo.get_items(2101), [("roadblock", 2)])

        self.assertFalse(await inventory_repo.use_item_from_db(2101, "remote_dice"))


class MonopolyRepositoryTests(RepositoryIntegrationTestCase):
    async def test_monopoly_repo_player_lifecycle_and_property_flow(self):
        await self.create_user(3001, money=5000, name="Owner")
        await self.create_user(3002, money=3000, name="Visitor")

        player = await monopoly_repo.ensure_player(3001)
        self.assertEqual(player, (0, "normal", 0, 0, 0))

        await monopoly_repo.activate_next_dice_fixed(3001)
        state = await monopoly_repo.get_player_state(3001)
        self.assertEqual(state[3], 6)

        await monopoly_repo.clear_next_dice_fixed(3001)
        state = await monopoly_repo.get_player_state(3001)
        self.assertEqual(state[3], 0)

        new_pos, passed_go = await monopoly_repo.move_player_with_pass_go(3001, 18, 4, 20, 500)
        self.assertEqual(new_pos, 2)
        self.assertTrue(passed_go)
        self.assertAlmostEqual(await user_repo.get_user_money(3001), 5500)

        success, reason = await monopoly_repo.buy_property(3001, 7, 1200)
        self.assertTrue(success)
        self.assertIsNone(reason)
        self.assertEqual(await monopoly_repo.get_property_owner(7), 3001)
        self.assertAlmostEqual(await user_repo.get_user_money(3001), 4300)

        await monopoly_repo.place_roadblock(7)
        await monopoly_repo.pay_rent(3002, 3001, 300, map_id=7, clear_roadblock=True)
        self.assertAlmostEqual(await user_repo.get_user_money(3002), 2700)
        self.assertAlmostEqual(await user_repo.get_user_money(3001), 4600)
        property_state = await monopoly_repo.get_property_state(7)
        self.assertEqual(property_state[:3], (3001, 1, None))
        self.assertEqual(property_state[3], 1200)
        self.assertGreater(property_state[4], 0)

    async def test_monopoly_repo_property_maintenance_and_reclaim(self):
        await self.create_user(3004, money=5000, name="Maintainer")

        success, _ = await monopoly_repo.buy_property(3004, 11, 1000)
        self.assertTrue(success)
        success, _ = await monopoly_repo.buy_property(3004, 12, 1200)
        self.assertTrue(success)

        rows = await monopoly_repo.get_owned_properties(3004)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row[2] > 0 for row in rows))

        success, payload, total_fee = await monopoly_repo.maintain_all_properties(3004, 50, 999999)
        self.assertTrue(success)
        self.assertEqual(len(payload), 2)
        self.assertEqual(total_fee, 100)
        self.assertAlmostEqual(await user_repo.get_user_money(3004), 2700)

        rows = await monopoly_repo.get_owned_properties(3004)
        self.assertEqual(rows, [(11, 1, 999999), (12, 1, 999999)])

        notice_rows = await monopoly_repo.get_properties_needing_maintenance_notice(990000, 10000)
        self.assertEqual([row[0] for row in notice_rows], [11, 12])
        await monopoly_repo.mark_property_maintenance_notice_sent(11)
        await monopoly_repo.mark_property_maintenance_notice_sent(12)
        self.assertEqual(await monopoly_repo.get_properties_needing_maintenance_notice(990000, 10000), [])

        reclaimed = await monopoly_repo.reclaim_expired_properties(1000000, 0.10)
        self.assertEqual(reclaimed, [(11, 3004, 1000.0, 100.0), (12, 3004, 1200.0, 120.0)])
        self.assertEqual(await monopoly_repo.get_owned_property_count(3004), 0)
        self.assertAlmostEqual(await user_repo.get_user_money(3004), 2920)

    async def test_monopoly_repo_jail_bail_and_bankruptcy(self):
        await self.create_user(3003, money=2000, name="Jailed")

        await monopoly_repo.ensure_player(3003)
        await monopoly_repo.send_player_to_jail(3003)
        state = await monopoly_repo.get_player_state(3003)
        self.assertEqual(state[0], 10)
        self.assertEqual(state[1], "in_jail")
        self.assertEqual(state[2], 3)

        await monopoly_repo.decrement_jail_turn_and_add_bad_luck(3003, 3)
        state = await monopoly_repo.get_player_state(3003)
        self.assertEqual(state[2], 2)
        self.assertEqual(state[4], 1)

        success, money = await monopoly_repo.pay_bail(3003, 500)
        self.assertTrue(success)
        self.assertEqual(money, 2000)
        self.assertAlmostEqual(await user_repo.get_user_money(3003), 1500)
        state = await monopoly_repo.get_player_state(3003)
        self.assertEqual(state[1], "normal")
        self.assertEqual(state[2], 0)

        success, _ = await monopoly_repo.buy_property(3003, 9, 1000)
        self.assertTrue(success)
        self.assertEqual(await monopoly_repo.get_owned_property_count(3003), 1)

        await monopoly_repo.bankrupt_player(3003)
        self.assertAlmostEqual(await user_repo.get_user_money(3003), 0)
        self.assertEqual(await monopoly_repo.get_owned_property_count(3003), 0)
        self.assertEqual(await monopoly_repo.get_player_position(3003), 0)


class TitleRepositoryTests(RepositoryIntegrationTestCase):
    async def test_title_repo_unlocks_equips_and_lists_titles(self):
        await self.create_user(4001, money=1000, name="Titled")

        self.assertFalse(await title_repo.check_title_owned(4001, "hero"))
        await title_repo.unlock_title(4001, "hero")
        await title_repo.unlock_title(4001, "legend")

        self.assertTrue(await title_repo.check_title_owned(4001, "hero"))
        self.assertEqual(await title_repo.get_user_titles(4001), ["hero", "legend"])

        await title_repo.equip_user_title(4001, "传奇猫猫")
        citizen = await user_repo.get_citizen(4001)
        self.assertEqual(citizen[6], "传奇猫猫")


class RankingRepositoryTests(RepositoryIntegrationTestCase):
    async def test_ranking_repo_returns_sorted_money_and_property_leaders(self):
        await self.create_user(5001, money=8000, name="Alpha")
        await self.create_user(5002, money=6000, name="Beta")
        await self.create_user(5003, money=9000, name="Gamma")

        money_rows = await ranking_repo.get_top_money_users(limit=2)
        self.assertEqual(money_rows, [("Gamma", 9000), ("Alpha", 8000)])

        await monopoly_repo.buy_property(5001, 1, 1000)
        await monopoly_repo.buy_property(5001, 2, 1000)
        await monopoly_repo.buy_property(5002, 3, 1000)

        property_rows = await ranking_repo.get_top_property_owners(limit=3)
        self.assertEqual(property_rows[0], ("Alpha", 2))
        self.assertEqual(property_rows[1], ("Beta", 1))


class ProfileFeatureRepositoryTests(RepositoryIntegrationTestCase):
    async def test_profile_repository_uses_current_users_schema(self):
        async with aiosqlite.connect(self.db_path) as db:
            self.assertIsNone(await profile_repository.get_citizen(db, 6001))

            await profile_repository.create_citizen(db, 6001, "FeatureCat", "布偶喵", "重点色", 1888)
            citizen = await profile_repository.get_citizen(db, 6001)
            self.assertEqual(citizen[1], "FeatureCat")
            self.assertEqual(citizen[2], "布偶喵")
            self.assertEqual(citizen[3], "重点色")
            self.assertEqual(citizen[4], 1888)
            self.assertEqual(citizen[5], "normal")
            self.assertEqual(citizen[6], "无名之辈")

            await profile_repository.update_money(db, 6001, 112)
            await profile_repository.unlock_title(db, 6001, "18")
            await profile_repository.unlock_title(db, 6001, "23")
            self.assertTrue(await profile_repository.check_title_owned(db, 6001, "18"))
            self.assertEqual(await profile_repository.get_user_titles(db, 6001), ["18", "23"])

            await profile_repository.equip_title(db, 6001, "喵尔街之狼")
            citizen = await profile_repository.get_citizen(db, 6001)
            self.assertEqual(citizen[4], 2000)
            self.assertEqual(citizen[6], "喵尔街之狼")
