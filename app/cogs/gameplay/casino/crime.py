from __future__ import annotations

import random

import discord
from discord.ext import commands

from app.db.repositories.casino_repo import (
    apply_bank_robbery_success,
    bribe_for_release,
    consume_daily_guard_duel_attempt,
    consume_daily_robbery_attempt,
    ensure_casino_user,
    extend_jail_sentence,
    get_active_sentence_end,
    get_casino_stats,
    get_daily_crime_counters,
    get_total_bank_pool,
    get_wallet_and_level,
    has_active_buff,
    record_player_robbery_success,
    release_from_jail,
    send_user_to_jail,
    transfer_money_between_users,
)
from app.db.repositories.user_repo import get_citizen, update_money
from app.features.casino import service as casino_service


ROB_IMAGE_URL = "https://i.postimg.cc/hGtdYF6z/image.png"
JAIL_IMAGE_URL = "https://img.cdn1.vip/i/689ad57a9a4cf_1754977658.webp"
BANK_VAULT_BASE = 10_000_000_000


async def build_crime_embed(user_id: int, user_name: str):
    await ensure_casino_user(user_id)
    sentence_end = await get_active_sentence_end(user_id)
    stats = await get_casino_stats(user_id)
    jail_count = stats[2]
    today = casino_service.get_beijing_today()
    robberies_today, robbery_successes_today, guard_duels_today = await get_daily_crime_counters(user_id, today)

    embed = discord.Embed(title="🔫 犯罪中心", color=0xC0392B)
    embed.set_thumbnail(url=ROB_IMAGE_URL if sentence_end is None else JAIL_IMAGE_URL)
    if sentence_end is None:
        embed.description = f"欢迎来到地下黑市，**{user_name}**。这里管理打劫、坐牢、贿赂和越狱。"
    else:
        remain = casino_service.format_remaining_minutes(sentence_end)
        embed.description = f"🚨 你当前正在服刑，剩余约 **{remain}** 分钟。可以尝试贿赂或对决守卫。"
    embed.add_field(name="累计入狱次数", value=f"**{jail_count}**", inline=True)
    embed.add_field(name="银行大劫案成功率", value=f"**{casino_service.BANK_ROB_SUCCESS_RATE * 100:.0f}%**", inline=True)
    embed.add_field(
        name="今日作案额度",
        value=(
            f"打劫剩余：**{max(0, min(casino_service.MAX_ROBBERIES_PER_DAY - robberies_today, casino_service.MAX_ROBBERY_SUCCESSES_PER_DAY - robbery_successes_today))}** "
            f"(尝试 {robberies_today}/{casino_service.MAX_ROBBERIES_PER_DAY}，成功 {robbery_successes_today}/{casino_service.MAX_ROBBERY_SUCCESSES_PER_DAY})\n"
            f"对决剩余：**{max(0, casino_service.MAX_GUARD_DUELS_PER_DAY - guard_duels_today)} / {casino_service.MAX_GUARD_DUELS_PER_DAY}**"
        ),
        inline=False,
    )
    return embed


async def resolve_robbery_against_target(interaction: discord.Interaction, robber_id: int, target: discord.abc.User):
    if target.id == robber_id:
        return await interaction.response.send_message("🚫 不能打劫自己。", ephemeral=True)
    if target.bot:
        return await interaction.response.send_message("🚫 机器人不参与犯罪玩法。", ephemeral=True)

    victim = await get_citizen(target.id)
    if not victim:
        return await interaction.response.send_message(f"🚫 **{target.display_name}** 还没注册小镇档案。", ephemeral=True)

    current_sentence = await get_active_sentence_end(robber_id)
    if current_sentence is not None:
        remain = casino_service.format_remaining_minutes(current_sentence)
        return await interaction.response.send_message(f"🚨 你还在坐牢，剩余约 **{remain}** 分钟。", ephemeral=True)

    today = casino_service.get_beijing_today()
    robberies_today, robbery_successes_today, _guard_duels_today = await get_daily_crime_counters(robber_id, today)
    if (
        robberies_today >= casino_service.MAX_ROBBERIES_PER_DAY
        or robbery_successes_today >= casino_service.MAX_ROBBERY_SUCCESSES_PER_DAY
    ):
        return await interaction.response.send_message(
            (
                "🚫 你今天的打劫额度已经用完了。"
                f"尝试上限 **{casino_service.MAX_ROBBERIES_PER_DAY}** 次，"
                f"成功上限 **{casino_service.MAX_ROBBERY_SUCCESSES_PER_DAY}** 次。"
            ),
            ephemeral=True,
        )

    _thief_wallet, thief_level = await get_wallet_and_level(robber_id)
    victim_wallet, victim_level = await get_wallet_and_level(target.id)
    if victim_wallet <= 0:
        return await interaction.response.send_message(f"💨 **{target.display_name}** 身上没有可抢的喵币。", ephemeral=True)
    await consume_daily_robbery_attempt(robber_id, today)

    success_rate = casino_service.calculate_player_rob_success_rate(thief_level, victim_level)
    if await has_active_buff(target.id, "rob_protection"):
        success_rate = max(casino_service.PLAYER_ROB_SUCCESS_MIN_RATE, success_rate * 0.7)

    if random.random() < success_rate:
        loot = casino_service.determine_player_robbery_loot(victim_wallet)
        await transfer_money_between_users(target.id, robber_id, loot)
        await record_player_robbery_success(robber_id, loot, today=today)
        embed = discord.Embed(title="🔫 打劫成功", color=0x2ECC71)
        embed.set_image(url=ROB_IMAGE_URL)
        embed.description = (
            f"你从 **{target.display_name}** 身上抢到了 **{loot}** 喵币。\n"
            f"本次成功率约 **{success_rate * 100:.0f}%**。"
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    wallet_after_attempt, _thief_level = await get_wallet_and_level(robber_id)
    fine_rate = random.randint(15, 30) / 100
    fine = int(wallet_after_attempt * fine_rate)
    if fine > 0:
        await update_money(robber_id, -fine)
    await send_user_to_jail(robber_id, casino_service.JAIL_MINUTES_ON_FAILED_ROB)
    embed = discord.Embed(title="👮 打劫失败", color=0xE74C3C)
    embed.set_image(url=JAIL_IMAGE_URL)
    embed.description = (
        f"你被 **{target.display_name}** 当场反制，入狱 **{casino_service.JAIL_MINUTES_ON_FAILED_ROB}** 分钟。\n"
        f"慌乱中还掉了 **{fine}** 喵币（约 {int(fine_rate * 100)}% 身家）。"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


class RobPlayerModal(discord.ui.Modal):
    def __init__(self, user_id: int):
        super().__init__(title="打劫目标")
        self.user_id = user_id
        self.add_item(
            discord.ui.InputText(
                label="输入目标用户 ID 或 @提及",
                placeholder="例如 123456789012345678 或 <@123456789012345678>",
                required=True,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        raw_value = self.children[0].value.strip()
        target_id_text = raw_value.replace("<@", "").replace("!", "").replace(">", "").strip()
        if not target_id_text.isdigit():
            return await interaction.response.send_message("🚫 请输入有效的用户 ID 或 @提及。", ephemeral=True)

        target_id = int(target_id_text)
        target = interaction.guild.get_member(target_id) if interaction.guild else None
        if target is None:
            target = interaction.client.get_user(target_id)
        if target is None:
            try:
                target = await interaction.client.fetch_user(target_id)
            except Exception:
                target = None
        if target is None:
            return await interaction.response.send_message("🚫 找不到这个目标用户。", ephemeral=True)

        await resolve_robbery_against_target(interaction, self.user_id, target)


class CrimePanelView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("这不是你的犯罪面板。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="打劫玩家", style=discord.ButtonStyle.primary, emoji="🔫", row=0)
    async def rob_player_btn(self, button, interaction):
        await interaction.response.send_modal(RobPlayerModal(self.user_id))

    @discord.ui.button(label="打劫银行", style=discord.ButtonStyle.danger, emoji="🏦", row=0)
    async def rob_bank_btn(self, button, interaction):
        current_sentence = await get_active_sentence_end(self.user_id)
        if current_sentence is not None:
            remain = casino_service.format_remaining_minutes(current_sentence)
            return await interaction.response.send_message(f"🚨 你还在坐牢，剩余约 **{remain}** 分钟。", ephemeral=True)

        today = casino_service.get_beijing_today()
        robberies_today, robbery_successes_today, _guard_duels_today = await get_daily_crime_counters(self.user_id, today)
        if (
            robberies_today >= casino_service.MAX_ROBBERIES_PER_DAY
            or robbery_successes_today >= casino_service.MAX_ROBBERY_SUCCESSES_PER_DAY
        ):
            return await interaction.response.send_message(
                (
                    "🚫 你今天的打劫额度已经用完了。"
                    f"尝试上限 **{casino_service.MAX_ROBBERIES_PER_DAY}** 次，"
                    f"成功上限 **{casino_service.MAX_ROBBERY_SUCCESSES_PER_DAY}** 次。"
                ),
                ephemeral=True,
            )
        await consume_daily_robbery_attempt(self.user_id, today)

        if random.random() < casino_service.BANK_ROB_SUCCESS_RATE:
            bank_pool = await get_total_bank_pool()
            loot = casino_service.determine_bank_robbery_loot(BANK_VAULT_BASE + bank_pool)
            await apply_bank_robbery_success(self.user_id, loot, today=today)
            embed = discord.Embed(title="🏦💥 银行大劫案成功", color=0xF1C40F)
            embed.set_image(url=ROB_IMAGE_URL)
            embed.description = f"你成功卷走 **{loot}** 喵币，银行活期账户统一承受了 2% 损耗。"
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        wallet_after_attempt, _thief_level = await get_wallet_and_level(self.user_id)
        fine_rate = random.randint(15, 30) / 100
        fine = int(wallet_after_attempt * fine_rate)
        if fine > 0:
            await update_money(self.user_id, -fine)
        await send_user_to_jail(self.user_id, casino_service.JAIL_MINUTES_ON_FAILED_ROB)
        embed = discord.Embed(title="🚓 银行打劫失败", color=0xE74C3C)
        embed.set_image(url=JAIL_IMAGE_URL)
        embed.description = (
            f"保安把你直接送进监狱 **{casino_service.JAIL_MINUTES_ON_FAILED_ROB}** 分钟。\n"
            f"混乱中你还丢了 **{fine}** 喵币（约 {int(fine_rate * 100)}% 身家）。"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="贿赂守卫", style=discord.ButtonStyle.success, emoji="💸", row=1)
    async def bribe_btn(self, button, interaction):
        sentence_end = await get_active_sentence_end(self.user_id)
        if sentence_end is None:
            return await interaction.response.send_message("🟢 你现在是自由身，不需要贿赂守卫。", ephemeral=True)

        stats = await get_casino_stats(self.user_id)
        today = casino_service.get_beijing_today()
        bribes_today = stats[4] if stats[5] == today else 0
        if bribes_today >= casino_service.MAX_BRIBES_PER_DAY:
            return await interaction.response.send_message("🚫 今天已经贿赂太多次了，守卫不再收钱。", ephemeral=True)

        cost = random.randint(1000, 10000)
        success, reason, payload = await bribe_for_release(self.user_id, cost, today)
        if not success:
            if reason == "insufficient_wallet":
                return await interaction.response.send_message(
                    f"🚫 你只有 **{payload}** 喵币，不够支付 **{cost}**。",
                    ephemeral=True,
                )
            return await interaction.response.send_message("🚫 贿赂失败，请稍后再试。", ephemeral=True)
        await interaction.response.send_message(f"💸 你花了 **{cost}** 喵币，守卫收钱放人了。", ephemeral=True)

    @discord.ui.button(label="对决守卫", style=discord.ButtonStyle.secondary, emoji="⚔️", row=1)
    async def duel_btn(self, button, interaction):
        sentence_end = await get_active_sentence_end(self.user_id)
        if sentence_end is None:
            return await interaction.response.send_message("🟢 你现在是自由身，不需要越狱。", ephemeral=True)

        today = casino_service.get_beijing_today()
        _robberies_today, _robbery_successes_today, guard_duels_today = await get_daily_crime_counters(self.user_id, today)
        if guard_duels_today >= casino_service.MAX_GUARD_DUELS_PER_DAY:
            return await interaction.response.send_message(
                f"🚫 你今天已经把守卫打烦了，明天再来。上限 **{casino_service.MAX_GUARD_DUELS_PER_DAY}** 次。",
                ephemeral=True,
            )
        await consume_daily_guard_duel_attempt(self.user_id, today)

        player_total, guard_total = casino_service.roll_guard_duel()
        embed = discord.Embed(title="⚔️ 越狱对决", color=0xE67E22)
        embed.add_field(name="你", value=str(player_total), inline=True)
        embed.add_field(name="守卫", value=str(guard_total), inline=True)
        if player_total > guard_total:
            await release_from_jail(self.user_id)
            embed.color = 0x2ECC71
            embed.description = "🎉 你打赢了守卫，成功越狱。"
        else:
            wallet, _thief_level = await get_wallet_and_level(self.user_id)
            fine_rate = random.randint(3, 5) / 100
            fine = int(wallet * fine_rate)
            if fine > 0:
                await update_money(self.user_id, -fine)
            new_end = await extend_jail_sentence(self.user_id, casino_service.DUEL_JAIL_EXTENSION_MINUTES)
            remain = casino_service.format_remaining_minutes(new_end)
            embed.color = 0xE74C3C
            embed.description = (
                f"👎 越狱失败，刑期延长 **{casino_service.DUEL_JAIL_EXTENSION_MINUTES}** 分钟，剩余约 **{remain}** 分钟。\n"
                f"还赔了 **{fine}** 喵币（约 {int(fine_rate * 100)}% 身家）。"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="刷新状态", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, button, interaction):
        embed = await build_crime_embed(self.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)


async def open_crime_panel(interaction: discord.Interaction, user_id: int):
    embed = await build_crime_embed(user_id, interaction.user.display_name)
    await interaction.response.send_message(embed=embed, view=CrimePanelView(user_id), ephemeral=True)


class CrimeCenter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(CrimeCenter(bot))
