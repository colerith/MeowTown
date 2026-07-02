from __future__ import annotations

import math
import random

import discord
from discord.ext import commands

from app.db.repositories.casino_repo import (
    apply_game_result,
    ensure_casino_user,
    get_buff_bonus_multiplier,
    get_casino_stats,
    get_gambling_profile,
    update_gambling_profile,
)
from app.db.repositories.user_repo import get_citizen
from app.features.casino import service as casino_service


SLOT_IMAGE_URL = "https://i.postimg.cc/t4Dv4KDt/slot.png"
DICE_IMAGE_URL = "https://i.postimg.cc/J4RhmP0b/dice.png"
POKER_IMAGE_URL = "https://img.cdn1.vip/i/689ad57b220c6_1754977659.webp"
ROULETTE_IMAGE_URL = "https://i.postimg.cc/MpDBtZPJ/image.png"

MIN_BET = 100
DEFAULT_CUSTOM_BET = 500
DEFAULT_RANDOM_MIN_PERCENT = 5
DEFAULT_RANDOM_MAX_PERCENT = 15


def clamp_bet(balance: int, bet: int) -> int:
    safe_balance = max(0, int(balance or 0))
    if safe_balance <= 0:
        return 0
    return min(safe_balance, max(MIN_BET, int(bet)))


def format_bet_mode(profile: dict) -> str:
    mode = profile.get("bet_mode", "random")
    if mode == "custom":
        return f"自选投入 **{profile['custom_bet']}** 喵币"
    if mode == "last":
        return f"延续上次投入 **{profile['last_bet']}** 喵币"
    return f"随机投入钱包的 **{profile['random_min_percent']}% - {profile['random_max_percent']}%**"


def roll_random_bet(balance: int, profile: dict) -> int:
    min_percent = max(1, int(profile.get("random_min_percent", DEFAULT_RANDOM_MIN_PERCENT)))
    max_percent = max(min_percent, int(profile.get("random_max_percent", DEFAULT_RANDOM_MAX_PERCENT)))
    rolled_percent = random.randint(min_percent, max_percent)
    return clamp_bet(balance, int(balance * rolled_percent / 100))


async def resolve_bet_for_user(user_id: int):
    citizen = await get_citizen(user_id)
    if not citizen:
        return None, None, None, "not_citizen"

    balance = int(citizen[4] or 0)
    profile = await get_gambling_profile(user_id)
    if profile is None:
        return citizen, None, None, "profile_missing"

    if balance < MIN_BET:
        return citizen, profile, None, "balance_too_low"

    mode = profile.get("bet_mode", "random")
    if mode == "custom":
        bet = clamp_bet(balance, profile.get("custom_bet", DEFAULT_CUSTOM_BET))
    elif mode == "last":
        last_bet = int(profile.get("last_bet") or 0)
        if last_bet < MIN_BET:
            return citizen, profile, None, "last_bet_missing"
        bet = clamp_bet(balance, last_bet)
    else:
        bet = roll_random_bet(balance, profile)

    if bet < MIN_BET:
        return citizen, profile, None, "balance_too_low"

    return citizen, profile, bet, "ok"


async def build_gambling_embed(user_id: int, user_name: str):
    await ensure_casino_user(user_id)
    stats = await get_casino_stats(user_id)
    profile = await get_gambling_profile(user_id)
    wins, losses = stats[0], stats[1]
    total_rounds = wins + losses
    win_rate = (wins / total_rounds * 100) if total_rounds else 0
    bonus_multiplier = await get_buff_bonus_multiplier(user_id)

    embed = discord.Embed(title="🎰 喵喵娱乐城", color=0xF1C40F)
    embed.description = f"欢迎光临，**{user_name}**。这里是发牌姬核心玩法并入小镇后的娱乐城大厅。"
    embed.add_field(
        name="📊 赌博战绩",
        value=f"胜场 **{wins}**\n败场 **{losses}**\n胜率 **{win_rate:.1f}%**",
        inline=True,
    )
    embed.add_field(
        name="✨ 当前奖金倍率",
        value=f"**x{bonus_multiplier:.2f}**\n好运符、皇家赌约、筹码校准器都会影响这里",
        inline=True,
    )
    embed.add_field(name="可玩项目", value="老虎机 / 2d6 / 德州 / 21点 / 俄罗斯轮盘", inline=True)
    embed.add_field(
        name="💵 当前下注模式",
        value=(
            f"{format_bet_mode(profile)}\n"
            f"上次实际下注：**{profile['last_bet']}** 喵币"
        ),
        inline=False,
    )
    embed.set_footer(text="按钮版娱乐城已并入市民档案，不再单独走 slash 指令。")
    return embed


class CustomBetModal(discord.ui.Modal):
    def __init__(self, parent_view, current_value: int):
        super().__init__(title="设置自选投入")
        self.parent_view = parent_view
        self.add_item(
            discord.ui.InputText(
                label="固定投入金额",
                value=str(current_value),
                placeholder="请输入每局要投入的喵币",
                required=True,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            amount = casino_service.parse_positive_int(self.children[0].value)
        except Exception:
            return await interaction.response.send_message("🚫 请输入大于 0 的整数金额。", ephemeral=True)

        amount = max(MIN_BET, amount)
        await update_gambling_profile(
            self.parent_view.user_id,
            bet_mode="custom",
            custom_bet=amount,
        )
        embed = await build_gambling_embed(self.parent_view.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class RandomBetSettingsModal(discord.ui.Modal):
    def __init__(self, parent_view, min_percent: int, max_percent: int):
        super().__init__(title="设置随机投入范围")
        self.parent_view = parent_view
        self.add_item(
            discord.ui.InputText(
                label="最小百分比",
                value=str(min_percent),
                placeholder="例如 5",
                required=True,
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="最大百分比",
                value=str(max_percent),
                placeholder="例如 15",
                required=True,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            min_percent = casino_service.parse_positive_int(self.children[0].value)
            max_percent = casino_service.parse_positive_int(self.children[1].value)
        except Exception:
            return await interaction.response.send_message("🚫 百分比必须是正整数。", ephemeral=True)

        min_percent = max(1, min(min_percent, 100))
        max_percent = max(min_percent, min(max_percent, 100))
        await update_gambling_profile(
            self.parent_view.user_id,
            bet_mode="random",
            random_min_percent=min_percent,
            random_max_percent=max_percent,
        )
        embed = await build_gambling_embed(self.parent_view.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class RussianRouletteView(discord.ui.View):
    def __init__(self, user_id: int, bet: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bet = bet
        self.bullet = casino_service.roll_roulette_chamber()
        self.shot = 1
        self.winnings = 0
        self.is_over = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("这不是你的俄罗斯轮盘局。", ephemeral=True)
            return False
        return True

    def create_embed(self):
        if self.is_over:
            return None
        survival_prob = ["5/6", "4/5", "3/4", "2/3", "1/2"][self.shot - 1]
        embed = discord.Embed(
            title="🔫 俄罗斯轮盘",
            description=f"第 **{self.shot}** 枪\n当前奖池：**{self.winnings}** 喵币\n存活概率：**{survival_prob}**",
            color=discord.Color.dark_red(),
        )
        embed.set_image(url=ROULETTE_IMAGE_URL)
        embed.set_footer(text="继续开枪会抬高奖池，但一旦中枪会直接亏掉本轮赌注。")
        return embed

    async def _finish_round(self, interaction: discord.Interaction, survived: bool, cashed_out: bool = False):
        self.is_over = True
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(title="🔫 俄罗斯轮盘结算", color=discord.Color.red())
        embed.set_image(url=ROULETTE_IMAGE_URL)
        if not survived:
            await apply_game_result(self.user_id, -self.bet, loss=True)
            embed.description = f"💥 枪响了，你本轮失去 **{self.bet}** 喵币。"
            embed.color = discord.Color.red()
        else:
            await apply_game_result(self.user_id, self.winnings, win=True)
            if cashed_out:
                embed.description = f"🏃 你及时收手，带走 **{self.winnings}** 喵币。"
            else:
                embed.description = f"🎉 你硬生生撑到了最后，卷走 **{self.winnings}** 喵币。"
            embed.color = discord.Color.green()

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="开枪", style=discord.ButtonStyle.danger, emoji="💥")
    async def fire_btn(self, button, interaction):
        if self.shot == self.bullet:
            return await self._finish_round(interaction, survived=False)

        self.winnings += math.floor(self.bet * casino_service.roulette_survival_multiplier(self.shot))
        self.shot += 1
        if self.shot > 5:
            return await self._finish_round(interaction, survived=True, cashed_out=False)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="收手", style=discord.ButtonStyle.success, emoji="🏃")
    async def stop_btn(self, button, interaction):
        await self._finish_round(interaction, survived=True, cashed_out=True)


class BlackJackView(discord.ui.View):
    def __init__(self, user_id: int, bet: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.bet = bet
        self.deck = casino_service.create_poker_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.is_over = False
        for _ in range(2):
            self.player_hand.append(self.deck.pop())
            self.dealer_hand.append(self.deck.pop())

    def _embed(self, result_text=None, reveal_dealer=False, color=discord.Color.blue()):
        player_score = casino_service.calculate_blackjack_score(self.player_hand)
        dealer_score = casino_service.calculate_blackjack_score(self.dealer_hand) if reveal_dealer else "?"
        dealer_cards = casino_service.format_cards(self.dealer_hand) if reveal_dealer else f"[❓] {casino_service.format_cards(self.dealer_hand[1:])}"

        embed = discord.Embed(title=f"🃏 21点 - 底注 {self.bet}", color=color)
        embed.add_field(name=f"庄家: {dealer_score}", value=dealer_cards, inline=False)
        embed.add_field(name=f"你: {player_score}", value=casino_service.format_cards(self.player_hand), inline=False)
        if result_text:
            embed.description = result_text
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("这不是你的 21 点牌局。", ephemeral=True)
            return False
        return True

    async def _finish(self, interaction: discord.Interaction, result: str):
        self.is_over = True
        for child in self.children:
            child.disabled = True

        if result == "win":
            multiplier = await get_buff_bonus_multiplier(self.user_id)
            reward = int(self.bet * multiplier)
            await apply_game_result(self.user_id, reward, win=True)
            embed = self._embed(f"🎉 你赢了，结算 **{reward}** 喵币。", reveal_dealer=True, color=discord.Color.green())
        elif result == "loss":
            await apply_game_result(self.user_id, -self.bet, loss=True)
            embed = self._embed(f"💸 你输了，本轮失去 **{self.bet}** 喵币。", reveal_dealer=True, color=discord.Color.red())
        else:
            embed = self._embed("🤝 平局，这一轮不输不赢。", reveal_dealer=True, color=discord.Color.blurple())

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="要牌", style=discord.ButtonStyle.success, emoji="🃏")
    async def hit_btn(self, button, interaction):
        self.player_hand.append(self.deck.pop())
        if casino_service.calculate_blackjack_score(self.player_hand) > 21:
            return await self._finish(interaction, "loss")
        await interaction.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(label="停牌", style=discord.ButtonStyle.danger, emoji="✋")
    async def stand_btn(self, button, interaction):
        while casino_service.calculate_blackjack_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

        player_score = casino_service.calculate_blackjack_score(self.player_hand)
        dealer_score = casino_service.calculate_blackjack_score(self.dealer_hand)
        if dealer_score > 21 or player_score > dealer_score:
            return await self._finish(interaction, "win")
        if player_score < dealer_score:
            return await self._finish(interaction, "loss")
        return await self._finish(interaction, "push")


class GamblingPanelView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("这不是你的娱乐城面板。", ephemeral=True)
            return False
        return True

    async def _get_balance_and_bet(self):
        return await resolve_bet_for_user(self.user_id)

    async def _prepare_bet(self, interaction: discord.Interaction):
        citizen, profile, bet, status = await self._get_balance_and_bet()
        if status == "not_citizen":
            await interaction.response.send_message("🚫 你还不是小镇居民。", ephemeral=True)
            return None, None, None
        if status == "last_bet_missing":
            await interaction.response.send_message("🚫 你还没有上一次下注记录，请先切到自选投入或随机投入。", ephemeral=True)
            return None, None, None
        if status != "ok":
            await interaction.response.send_message("🚫 钱包太瘪了，至少要有 100 喵币才能开局。", ephemeral=True)
            return None, None, None
        if int(citizen[4] or 0) < bet:
            await interaction.response.send_message("🚫 当前钱包金额不足以完成这次下注。", ephemeral=True)
            return None, None, None
        return citizen, profile, bet

    @discord.ui.button(label="老虎机", style=discord.ButtonStyle.primary, emoji="🎰", row=0)
    async def slots_btn(self, button, interaction):
        citizen, _profile, bet = await self._prepare_bet(interaction)
        if citizen is None:
            return

        reels, payout = casino_service.roll_slots(bet)
        await update_gambling_profile(self.user_id, last_bet=bet)
        embed = discord.Embed(title="🎰 老虎机", color=0xF39C12)
        embed.set_image(url=SLOT_IMAGE_URL)
        embed.add_field(name="本轮投入", value=f"**{bet}** 喵币", inline=True)
        embed.add_field(name="结果", value=f"**[ {' | '.join(reels)} ]**", inline=False)

        if payout > 0:
            multiplier = await get_buff_bonus_multiplier(self.user_id)
            boosted_payout = int(payout * multiplier)
            delta = boosted_payout - bet
            await apply_game_result(self.user_id, delta, win=True)
            embed.description = f"🎉 命中奖励！基础奖金 **{payout}**，增益后结算 **{boosted_payout}**，净赚 **{delta}**。"
        else:
            await apply_game_result(self.user_id, -bet, loss=True)
            embed.description = f"💸 这轮没有中奖，失去 **{bet}** 喵币。"

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="骰子对赌", style=discord.ButtonStyle.success, emoji="🎲", row=0)
    async def dice_btn(self, button, interaction):
        citizen, _profile, bet = await self._prepare_bet(interaction)
        if citizen is None:
            return

        player_dice, dealer_dice, player_score, dealer_score = casino_service.roll_dice_battle()
        await update_gambling_profile(self.user_id, last_bet=bet)
        embed = discord.Embed(title="🎲 2d6 比大小", color=0x3498DB)
        embed.set_image(url=DICE_IMAGE_URL)
        embed.add_field(name="本轮投入", value=f"**{bet}** 喵币", inline=True)
        embed.add_field(name="你的点数", value=f"{player_dice[0]} + {player_dice[1]} = **{player_score}**", inline=False)
        embed.add_field(name="庄家点数", value=f"{dealer_dice[0]} + {dealer_dice[1]} = **{dealer_score}**", inline=False)

        if player_score > dealer_score:
            multiplier = await get_buff_bonus_multiplier(self.user_id)
            reward = int(bet * multiplier)
            await apply_game_result(self.user_id, reward, win=True)
            embed.description = f"👑 你赢了！按当前增益结算，本轮获得 **{reward}** 喵币。"
        elif player_score < dealer_score:
            await apply_game_result(self.user_id, -bet, loss=True)
            embed.description = f"💸 庄家收走了你的 **{bet}** 喵币。"
        else:
            embed.description = "🤝 平局，本轮赌注原路退回。"

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="德州扑克", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def poker_btn(self, button, interaction):
        citizen, _profile, bet = await self._prepare_bet(interaction)
        if citizen is None:
            return

        round_data = casino_service.deal_texas_holdem_round()
        await update_gambling_profile(self.user_id, last_bet=bet)
        embed = discord.Embed(title="🃏 德州扑克", color=discord.Color.dark_red())
        embed.set_image(url=POKER_IMAGE_URL)
        embed.add_field(name="本轮投入", value=f"**{bet}** 喵币", inline=True)
        embed.add_field(name="公共牌", value=casino_service.format_cards(round_data["community_cards"]), inline=False)
        embed.add_field(name=f"你的手牌 ({round_data['player_name']})", value=casino_service.format_cards(round_data["player_hand"]), inline=True)
        embed.add_field(name=f"庄家手牌 ({round_data['dealer_name']})", value=casino_service.format_cards(round_data["dealer_hand"]), inline=True)

        if round_data["player_rank"] > round_data["dealer_rank"]:
            multiplier = await get_buff_bonus_multiplier(self.user_id)
            reward = int(bet * multiplier)
            await apply_game_result(self.user_id, reward, win=True)
            embed.description = f"🎉 你用 **{round_data['player_name']}** 击败庄家，赢得 **{reward}** 喵币。"
            embed.color = discord.Color.green()
        elif round_data["player_rank"] < round_data["dealer_rank"]:
            await apply_game_result(self.user_id, -bet, loss=True)
            embed.description = f"💸 庄家用 **{round_data['dealer_name']}** 压过了你，本轮失去 **{bet}** 喵币。"
            embed.color = discord.Color.red()
        else:
            embed.description = f"🤝 双方都是 **{round_data['player_name']}**，本轮平局。"
            embed.color = discord.Color.blurple()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="21点", style=discord.ButtonStyle.success, emoji="🃏", row=1)
    async def blackjack_btn(self, button, interaction):
        citizen, _profile, bet = await self._prepare_bet(interaction)
        if citizen is None:
            return

        await update_gambling_profile(self.user_id, last_bet=bet)
        view = BlackJackView(self.user_id, bet)
        await interaction.response.send_message(embed=view._embed(), view=view, ephemeral=True)

    @discord.ui.button(label="俄罗斯轮盘", style=discord.ButtonStyle.danger, emoji="🔫", row=1)
    async def roulette_btn(self, button, interaction):
        citizen, _profile, bet = await self._prepare_bet(interaction)
        if citizen is None:
            return

        await update_gambling_profile(self.user_id, last_bet=bet)
        view = RussianRouletteView(self.user_id, bet)
        await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=True)

    @discord.ui.button(label="自选投入", style=discord.ButtonStyle.primary, emoji="💵", row=2)
    async def custom_bet_btn(self, button, interaction):
        profile = await get_gambling_profile(self.user_id)
        await interaction.response.send_modal(
            CustomBetModal(self, profile["custom_bet"] if profile else DEFAULT_CUSTOM_BET)
        )

    @discord.ui.button(label="延续上次", style=discord.ButtonStyle.secondary, emoji="♻️", row=2)
    async def last_bet_btn(self, button, interaction):
        profile = await get_gambling_profile(self.user_id)
        if not profile or int(profile.get("last_bet") or 0) < MIN_BET:
            return await interaction.response.send_message("🚫 你还没有可延续的上次下注记录。", ephemeral=True)
        await update_gambling_profile(self.user_id, bet_mode="last")
        embed = await build_gambling_embed(self.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="随机投入", style=discord.ButtonStyle.success, emoji="🎲", row=2)
    async def random_bet_btn(self, button, interaction):
        await update_gambling_profile(self.user_id, bet_mode="random")
        embed = await build_gambling_embed(self.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="随机设置", style=discord.ButtonStyle.secondary, emoji="⚙️", row=3)
    async def random_settings_btn(self, button, interaction):
        profile = await get_gambling_profile(self.user_id)
        await interaction.response.send_modal(
            RandomBetSettingsModal(
                self,
                profile["random_min_percent"] if profile else DEFAULT_RANDOM_MIN_PERCENT,
                profile["random_max_percent"] if profile else DEFAULT_RANDOM_MAX_PERCENT,
            )
        )

    @discord.ui.button(label="刷新战绩", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, button, interaction):
        embed = await build_gambling_embed(self.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)


async def open_gambling_panel(interaction: discord.Interaction, user_id: int):
    embed = await build_gambling_embed(user_id, interaction.user.display_name)
    await interaction.response.send_message(embed=embed, view=GamblingPanelView(user_id), ephemeral=True)


class GamblingHall(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(GamblingHall(bot))
