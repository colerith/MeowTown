from __future__ import annotations

from datetime import datetime

import discord
from discord.ext import commands

from app.db.repositories.casino_repo import (
    deposit_to_account,
    ensure_casino_user,
    get_bank_account,
    get_bank_leaderboard,
    withdraw_from_account,
)
from app.features.casino import service as casino_service
from app.features.economy.service import format_economy_guard_notice, format_economy_notice


BANK_IMAGE_URL = "https://i.postimg.cc/Xv1CSH62/image.png"


def build_bank_embed(account):
    _user_id, checking, savings, locked_until_raw, wallet = account
    embed = discord.Embed(title="🏦 喵喵银行", color=0x2ECC71)
    embed.set_thumbnail(url=BANK_IMAGE_URL)
    embed.add_field(name="👛 随身钱包", value=f"**{wallet}** 喵币", inline=False)
    embed.add_field(name="💳 活期账户", value=f"**{checking}** 喵币", inline=True)

    savings_status = "🔓 未锁定"
    if locked_until_raw and savings > 0:
        locked_until = datetime.fromisoformat(locked_until_raw)
        if casino_service.get_utc_now() < locked_until:
            savings_status = f"🔒 锁定至 {casino_service.format_beijing_time(locked_until)}"

    embed.add_field(name="🐷 定期账户", value=f"**{savings}** 喵币\n{savings_status}", inline=True)
    embed.set_footer(text="取款时若金额过大，会先经过银行清算与财政喵审查，偶尔还会触发银行跑路抵债。")
    return embed


class TransactionModal(discord.ui.Modal):
    def __init__(self, user_id: int, account_type: str, action: str):
        title_map = {
            ("checking", "deposit"): "存入活期",
            ("checking", "withdraw"): "取出活期",
            ("savings", "deposit"): "存入定期",
            ("savings", "withdraw"): "取出定期",
        }
        super().__init__(title=title_map[(account_type, action)])
        self.user_id = user_id
        self.account_type = account_type
        self.action = action
        self.add_item(discord.ui.InputText(label="金额", placeholder="请输入正整数喵币", required=True))

    async def callback(self, interaction: discord.Interaction):
        try:
            amount = casino_service.parse_positive_int(self.children[0].value)
        except Exception:
            return await interaction.response.send_message("🚫 金额必须是正整数。", ephemeral=True)

        await ensure_casino_user(self.user_id)
        if self.action == "deposit":
            locked_until = casino_service.compute_savings_unlock_time() if self.account_type == "savings" else None
            success, reason, payload = await deposit_to_account(
                self.user_id,
                amount,
                self.account_type,
                locked_until=locked_until,
            )
            if not success:
                if reason == "insufficient_wallet":
                    return await interaction.response.send_message(
                        f"🚫 钱包余额不足，当前只有 **{payload}** 喵币。",
                        ephemeral=True,
                    )
                return await interaction.response.send_message("🚫 存款失败，请稍后再试。", ephemeral=True)
            msg = f"✅ 已存入 **{amount}** 喵币到{'活期' if self.account_type == 'checking' else '定期'}账户。"
            guard_notice = format_economy_guard_notice(payload.get("auto_rebase_events"))
            if guard_notice:
                msg = f"{msg}\n{guard_notice}"
        else:
            success, reason, payload = await withdraw_from_account(self.user_id, amount, self.account_type)
            if not success:
                if reason == "insufficient_bank":
                    return await interaction.response.send_message(
                        f"🚫 账户余额不足，当前只有 **{payload}** 喵币。",
                        ephemeral=True,
                    )
                if reason == "savings_locked":
                    return await interaction.response.send_message(
                        f"🚫 定期存款仍在锁定中，将于 **{casino_service.format_beijing_time(payload)}** 解锁。",
                        ephemeral=True,
                    )
                return await interaction.response.send_message("🚫 取款失败，请稍后再试。", ephemeral=True)
            msg = (
                "💸 银行开始安排取款，清算部的肥猫们叼着算盘冲了出来。\n"
                f"{format_economy_notice(payload).replace('镇长', '银行董事会').replace('财政喵', '清算喵').replace('市政猫砂税', '跑路抵债手续费')}"
            )

        account = await get_bank_account(self.user_id)
        embed = build_bank_embed(account)
        embed.description = msg
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BankPanelView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("这不是你的银行面板。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="存活期", style=discord.ButtonStyle.success, emoji="💰", row=0)
    async def deposit_checking_btn(self, button, interaction):
        await interaction.response.send_modal(TransactionModal(self.user_id, "checking", "deposit"))

    @discord.ui.button(label="取活期", style=discord.ButtonStyle.primary, emoji="💸", row=0)
    async def withdraw_checking_btn(self, button, interaction):
        await interaction.response.send_modal(TransactionModal(self.user_id, "checking", "withdraw"))

    @discord.ui.button(label="存定期", style=discord.ButtonStyle.success, emoji="🐷", row=1)
    async def deposit_savings_btn(self, button, interaction):
        await interaction.response.send_modal(TransactionModal(self.user_id, "savings", "deposit"))

    @discord.ui.button(label="取定期", style=discord.ButtonStyle.primary, emoji="🔓", row=1)
    async def withdraw_savings_btn(self, button, interaction):
        await interaction.response.send_modal(TransactionModal(self.user_id, "savings", "withdraw"))

    @discord.ui.button(label="储户榜", style=discord.ButtonStyle.secondary, emoji="🏅", row=1)
    async def leaderboard_btn(self, button, interaction):
        rows = await get_bank_leaderboard(limit=10)
        embed = discord.Embed(title="🏦 喵喵银行储户榜", color=0xF1C40F)
        if not rows:
            embed.description = "目前还没有形成规模的储蓄用户。"
        else:
            lines = []
            for index, (user_id, total_deposit) in enumerate(rows, start=1):
                user = interaction.client.get_user(user_id)
                if user is None:
                    try:
                        user = await interaction.client.fetch_user(user_id)
                    except Exception:
                        user = None
                lines.append(f"**{index}.** {(user.display_name if user else f'用户 {user_id}')} - **{total_deposit}** 喵币")
            embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, button, interaction):
        account = await get_bank_account(self.user_id)
        await interaction.response.edit_message(embed=build_bank_embed(account), view=self)


async def open_bank_panel(interaction: discord.Interaction, user_id: int):
    await ensure_casino_user(user_id)
    account = await get_bank_account(user_id)
    await interaction.response.send_message(embed=build_bank_embed(account), view=BankPanelView(user_id), ephemeral=True)


class CasinoBank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(CasinoBank(bot))
