from __future__ import annotations

import math

import discord
from discord.ext import commands

from app.db.repositories.casino_repo import (
    apply_game_result,
    ensure_casino_user,
    get_buff_bonus_multiplier,
    get_casino_stats,
)
from app.db.repositories.user_repo import get_citizen
from app.features.casino import service as casino_service


SLOT_IMAGE_URL = "https://i.postimg.cc/t4Dv4KDt/slot.png"
DICE_IMAGE_URL = "https://i.postimg.cc/J4RhmP0b/dice.png"
POKER_IMAGE_URL = "https://img.cdn1.vip/i/689ad57b220c6_1754977659.webp"
ROULETTE_IMAGE_URL = "https://i.postimg.cc/MpDBtZPJ/image.png"


def get_auto_bet(balance):
    return min(max(100, int(balance * 0.05)), max(100, int(balance)))


async def build_gambling_embed(user_id: int, user_name: str):
    await ensure_casino_user(user_id)
    stats = await get_casino_stats(user_id)
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
    embed.set_footer(text="按钮版娱乐城已并入市民档案，不再单独走 slash 指令。")
    return embed


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
        citizen = await get_citizen(self.user_id)
        if not citizen:
            return None, None
        bet = get_auto_bet(int(citizen[4] or 0))
        return citizen, bet

    @discord.ui.button(label="老虎机", style=discord.ButtonStyle.primary, emoji="🎰", row=0)
    async def slots_btn(self, button, interaction):
        citizen, bet = await self._get_balance_and_bet()
        if not citizen:
            return await interaction.response.send_message("🚫 你还不是小镇居民。", ephemeral=True)
        if citizen[4] < bet:
            return await interaction.response.send_message("🚫 钱包太瘪了，至少要有 100 喵币才能开机。", ephemeral=True)

        reels, payout = casino_service.roll_slots(bet)
        embed = discord.Embed(title="🎰 老虎机", color=0xF39C12)
        embed.set_image(url=SLOT_IMAGE_URL)
        embed.add_field(name="自动下注", value=f"**{bet}** 喵币", inline=True)
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
        citizen, bet = await self._get_balance_and_bet()
        if not citizen:
            return await interaction.response.send_message("🚫 你还不是小镇居民。", ephemeral=True)
        if citizen[4] < bet:
            return await interaction.response.send_message("🚫 钱包太瘪了，至少要有 100 喵币才能开局。", ephemeral=True)

        player_dice, dealer_dice, player_score, dealer_score = casino_service.roll_dice_battle()
        embed = discord.Embed(title="🎲 2d6 比大小", color=0x3498DB)
        embed.set_image(url=DICE_IMAGE_URL)
        embed.add_field(name="自动下注", value=f"**{bet}** 喵币", inline=True)
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
        citizen, bet = await self._get_balance_and_bet()
        if not citizen:
            return await interaction.response.send_message("🚫 你还不是小镇居民。", ephemeral=True)
        if citizen[4] < bet:
            return await interaction.response.send_message("🚫 钱包太瘪了，至少要有 100 喵币才能开局。", ephemeral=True)

        round_data = casino_service.deal_texas_holdem_round()
        embed = discord.Embed(title="🃏 德州扑克", color=discord.Color.dark_red())
        embed.set_image(url=POKER_IMAGE_URL)
        embed.add_field(name="自动下注", value=f"**{bet}** 喵币", inline=True)
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
        citizen, bet = await self._get_balance_and_bet()
        if not citizen:
            return await interaction.response.send_message("🚫 你还不是小镇居民。", ephemeral=True)
        if citizen[4] < bet:
            return await interaction.response.send_message("🚫 钱包太瘪了，至少要有 100 喵币才能开局。", ephemeral=True)

        view = BlackJackView(self.user_id, bet)
        await interaction.response.send_message(embed=view._embed(), view=view, ephemeral=True)

    @discord.ui.button(label="俄罗斯轮盘", style=discord.ButtonStyle.danger, emoji="🔫", row=1)
    async def roulette_btn(self, button, interaction):
        citizen, bet = await self._get_balance_and_bet()
        if not citizen:
            return await interaction.response.send_message("🚫 你还不是小镇居民。", ephemeral=True)
        if citizen[4] < bet:
            return await interaction.response.send_message("🚫 钱包太瘪了，至少要有 100 喵币才能上桌。", ephemeral=True)

        view = RussianRouletteView(self.user_id, bet)
        await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=True)

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
