import unittest
from unittest.mock import patch

from app.features.monopoly import service as monopoly_service
from app.features.casino import service as casino_service
from app.features.profile import service as profile_service
from app.features.stock_market import service as stock_service
from app.cogs.gameplay import daily_signin
from app.shared.data import stock_data


class ProfileServiceTests(unittest.TestCase):
    @patch("app.features.profile.service.random.choice", side_effect=["中华田园喵", "橘色虎斑"])
    def test_generate_cat_identity_applies_special_bonus(self, _mock_choice):
        species, pattern, money, is_special = profile_service.generate_cat_identity()

        self.assertEqual(species, "中华田园喵")
        self.assertEqual(pattern, "橘色虎斑")
        self.assertEqual(money, profile_service.DEFAULT_MONEY + 5000)
        self.assertTrue(is_special)

    @patch("app.features.profile.service.random.choice", side_effect=["英国短毛喵", "纯黑"])
    def test_generate_cat_identity_uses_default_money_for_normal_combo(self, _mock_choice):
        species, pattern, money, is_special = profile_service.generate_cat_identity()

        self.assertEqual(species, "英国短毛喵")
        self.assertEqual(pattern, "纯黑")
        self.assertEqual(money, profile_service.DEFAULT_MONEY)
        self.assertFalse(is_special)

    @patch("app.features.profile.service.random.choice", side_effect=lambda options: options[0])
    def test_draw_random_title_picks_title_from_expected_rarity_pool(self, _mock_choice):
        cases = [
            (0.10, "N"),
            (0.70, "R"),
            (0.90, "SR"),
            (0.99, "SSR"),
        ]

        for random_value, expected_rarity in cases:
            with self.subTest(random_value=random_value, expected_rarity=expected_rarity):
                with patch("app.features.profile.service.random.random", return_value=random_value):
                    title_id, title_data = profile_service.draw_random_title()
                self.assertEqual(title_data["rarity"], expected_rarity)
                self.assertEqual(profile_service.TITLES[title_id], title_data)


class MonopolyServiceTests(unittest.TestCase):
    def test_build_status_text_combines_state_segments(self):
        status_text = monopoly_service.build_status_text("in_jail", 2, 6, 1)
        self.assertEqual(status_text, "🔒 禁闭中 (2回合) | 🎲 骰子锁定: 6 | 🌩️ 霉运值: 1/3")

    def test_calculate_upgrade_and_rent(self):
        tile = {"rent": [120, 240, 360]}

        self.assertEqual(monopoly_service.calculate_upgrade_cost(999), 499.5)
        self.assertEqual(monopoly_service.calculate_property_rent(tile, 2, None), 240)
        self.assertEqual(monopoly_service.calculate_property_rent(tile, 2, "roadblock"), 480)

    def test_handle_bad_luck_after_event(self):
        self.assertEqual(monopoly_service.handle_bad_luck_after_event(1, True), 2)
        self.assertEqual(monopoly_service.handle_bad_luck_after_event(2, False), 0)


class StockMarketServiceTests(unittest.TestCase):
    def test_parse_positive_int_and_amount(self):
        self.assertEqual(stock_service.parse_positive_int("12"), 12)
        self.assertEqual(stock_service.parse_positive_amount("12.345"), 12.35)

        with self.assertRaises(ValueError):
            stock_service.parse_positive_int("1.5")
        with self.assertRaises(ValueError):
            stock_service.parse_positive_int("0")
        with self.assertRaises(ValueError):
            stock_service.parse_positive_amount("-3")

    def test_format_market_trend(self):
        self.assertEqual(stock_service.format_market_trend(12, 2), ("🔼 +2.00", 20.0))
        self.assertEqual(stock_service.format_market_trend(8, -2), ("🔽 -2.00", -20.0))
        self.assertEqual(stock_service.format_market_trend(5, 0), ("⏺️ 0.00", 0.0))

    def test_summarize_portfolio(self):
        total_assets, content = stock_service.summarize_portfolio(
            1000,
            200,
            [("FISH", 10, 12.5), ("BOX", 4, 20)],
        )

        self.assertEqual(total_assets, 1005.0)
        self.assertIn("💰 现金: 1000.00", content)
        self.assertIn("💸 贷款: 200.00", content)
        self.assertIn("FISH: 10股 (≈125.00)", content)
        self.assertIn("BOX: 4股 (≈80.00)", content)

    def test_summarize_portfolio_without_positions(self):
        total_assets, content = stock_service.summarize_portfolio(500, 120, [])

        self.assertEqual(total_assets, 380)
        self.assertTrue(content.endswith("无"))

    def test_calculate_next_price_caps_bubble_stock(self):
        new_price, change_pct = stock_data.calculate_next_price("TOY", 10**18, 3)

        self.assertEqual(new_price, stock_data.STOCKS["TOY"]["max_price"])
        self.assertLess(change_pct, 0)

    def test_calculate_next_price_honors_price_floor(self):
        new_price, _change_pct = stock_data.calculate_next_price("BOX", 0.01, -3)

        self.assertEqual(new_price, stock_data.STOCKS["BOX"]["min_price"])


class DailySigninRewardTests(unittest.TestCase):
    @patch("app.cogs.gameplay.daily_signin.random.randint", return_value=7777777)
    @patch("app.cogs.gameplay.daily_signin.random.choices")
    def test_roll_signin_reward_uses_selected_tier_range_and_message(self, mock_choices, _mock_randint):
        target_tier = daily_signin.SIGNIN_REWARD_TIERS[4]
        mock_choices.return_value = [target_tier]

        reward, tier = daily_signin.roll_signin_reward()

        self.assertEqual(reward, 7777777)
        self.assertEqual(tier["key"], "legendary")
        self.assertEqual(tier["label"], "招财阶")
        self.assertLessEqual(tier["min"], reward)
        self.assertLessEqual(reward, tier["max"])
        self.assertIn("招财猫", tier["message"])


class CasinoServiceTests(unittest.TestCase):
    def test_calculate_rob_success_rate_has_floor(self):
        self.assertEqual(casino_service.calculate_player_rob_success_rate(5, 5), 0.5)
        self.assertEqual(casino_service.calculate_player_rob_success_rate(1, 100), 0.1)

    @patch("app.features.casino.service.random.choice", side_effect=["7️⃣", "7️⃣", "7️⃣"])
    def test_slots_supports_jackpot(self, _mock_choice):
        reels, payout = casino_service.roll_slots(100)
        self.assertEqual(reels, ["7️⃣", "7️⃣", "7️⃣"])
        self.assertEqual(payout, 7700)

    @patch("app.features.casino.service.random.randint", side_effect=[6, 6, 1, 1])
    def test_roll_dice_battle_returns_two_sides(self, _mock_randint):
        player_dice, dealer_dice, player_score, dealer_score = casino_service.roll_dice_battle()
        self.assertEqual(player_dice, [6, 6])
        self.assertEqual(dealer_dice, [1, 1])
        self.assertEqual(player_score, 12)
        self.assertEqual(dealer_score, 2)

    @patch("app.features.casino.service.random.randint", return_value=25)
    def test_determine_player_robbery_loot_uses_percent_window(self, _mock_randint):
        self.assertEqual(casino_service.determine_player_robbery_loot(100), 25)

    def test_blackjack_score_handles_aces(self):
        hand = [{"rank": "A", "suit": "♠️"}, {"rank": "9", "suit": "♥️"}, {"rank": "A", "suit": "♦️"}]
        self.assertEqual(casino_service.calculate_blackjack_score(hand), 21)

    @patch("app.features.casino.service.random.shuffle")
    def test_deal_texas_holdem_round_returns_complete_payload(self, _mock_shuffle):
        round_data = casino_service.deal_texas_holdem_round()
        self.assertEqual(len(round_data["player_hand"]), 2)
        self.assertEqual(len(round_data["dealer_hand"]), 2)
        self.assertEqual(len(round_data["community_cards"]), 5)
        self.assertIn(round_data["player_name"], casino_service.POKER_HAND_NAMES.values())
        self.assertIn(round_data["dealer_name"], casino_service.POKER_HAND_NAMES.values())
