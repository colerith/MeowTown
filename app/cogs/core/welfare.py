import random
import re
from dataclasses import dataclass, field

import discord
from discord.ext import commands
from discord.ui import InputText, Modal, View

from app.cogs.gameplay.cat import TOWN_GROUP
from app.db.repositories.stock_repo import grant_stock_shares
from app.db.repositories.user_repo import get_citizen, update_money
from app.db.repositories.welfare_repo import (
    begin_welfare_claim,
    cancel_welfare_claim,
    finish_welfare_claim,
    get_welfare_message,
    has_claimed_welfare,
    upsert_welfare_message,
)
from app.shared.data.stock_data import STOCKS
from app.shared.discord_roles import REGISTERED_ROLE_ID, grant_role_by_id

DEFAULT_WELFARE_TITLE = "🎁 喵喵小镇福利发放"
DEFAULT_WELFARE_BODY = "镇务处准备了一批新的镇民福利，已注册喵喵可点击下方按钮领取，每人仅限一次。"
MONEY_TIER_WEIGHTS = [
    ("暖爪档", 55, 0.00, 0.35),
    ("呼噜档", 25, 0.35, 0.65),
    ("幸运档", 12, 0.65, 0.85),
    ("星彩档", 6, 0.85, 0.96),
    ("传说档", 2, 0.96, 1.00),
]


@dataclass
class WelfareConfig:
    title: str = DEFAULT_WELFARE_TITLE
    body: str = DEFAULT_WELFARE_BODY
    mention_registered_role: bool = False
    role_rewards: list[dict] = field(default_factory=list)
    money_reward: dict = field(default_factory=lambda: {"enabled": False, "mode": "fixed", "fixed_amount": 0, "min_amount": 0, "max_amount": 0})
    stock_rewards: list[dict] = field(default_factory=list)


def _extract_int(value: str) -> int:
    digits = re.sub(r"[^\d]", "", value or "")
    if not digits:
        raise ValueError("缺少数字")
    return int(digits)


def parse_role_rewards(text: str):
    text = (text or "").strip()
    if not text:
        return []

    results = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        role_part, weight_part = re.split(r"[:,，\s]+", raw, maxsplit=1)
        role_id = _extract_int(role_part)
        weight = max(1, int(weight_part.strip()))
        results.append({"role_id": role_id, "weight": weight})
    return results


def parse_stock_rewards(text: str):
    text = (text or "").strip()
    if not text:
        return []

    results = []
    for line in text.splitlines():
        raw = line.strip().upper()
        if not raw:
            continue
        stock_part, quantity_part = re.split(r"[:,：，\s]+", raw, maxsplit=1)
        stock_id = stock_part.strip()
        if stock_id not in STOCKS:
            raise ValueError(f"未知股票代码: {stock_id}")
        quantity = max(1, int(quantity_part.strip()))
        results.append({"stock_id": stock_id, "quantity": quantity})
    return results


def parse_money_reward(mode_text: str, value_text: str):
    mode = (mode_text or "off").strip().lower()
    raw_value = (value_text or "").strip()
    if mode in {"off", "none", "关闭"}:
        return {"enabled": False, "mode": "fixed", "fixed_amount": 0, "min_amount": 0, "max_amount": 0}

    if mode == "fixed":
        amount = max(1, int(raw_value))
        return {"enabled": True, "mode": "fixed", "fixed_amount": amount, "min_amount": amount, "max_amount": amount}

    if mode == "range":
        normalized = raw_value.replace("~", "-").replace("～", "-")
        parts = [part.strip() for part in normalized.split("-", maxsplit=1)]
        if len(parts) != 2:
            raise ValueError("范围模式需填写 最小值-最大值")
        min_amount = max(1, int(parts[0]))
        max_amount = max(min_amount, int(parts[1]))
        return {
            "enabled": True,
            "mode": "range",
            "fixed_amount": 0,
            "min_amount": min_amount,
            "max_amount": max_amount,
        }

    raise ValueError("金额模式仅支持 off / fixed / range")


def summarize_role_rewards(entries, guild: discord.Guild | None):
    if not entries:
        return "未启用"
    lines = []
    for entry in entries:
        role = guild.get_role(int(entry["role_id"])) if guild else None
        role_name = role.name if role else f"身份组 {entry['role_id']}"
        lines.append(f"{role_name}（权重 {entry['weight']}）")
    return "\n".join(lines)


def summarize_money_reward(config: dict):
    if not config or not config.get("enabled"):
        return "未启用"
    if config.get("mode") == "fixed":
        return f"固定发放 **{config['fixed_amount']}** 喵币"
    return f"随机发放 **{config['min_amount']} - {config['max_amount']}** 喵币\n高额档位内置更低概率"


def summarize_stock_rewards(entries):
    if not entries:
        return "未启用"
    lines = []
    for entry in entries:
        stock = STOCKS.get(entry["stock_id"], {"name": entry["stock_id"]})
        lines.append(f"{stock['name']} {entry['quantity']} 股")
    return "\n".join(lines)


def build_welfare_embed(config: WelfareConfig, guild: discord.Guild | None = None, *, editor_name: str | None = None):
    embed = discord.Embed(title=config.title, description=config.body, color=0xF39C12)
    embed.add_field(name="🎭 身份组抽选", value=summarize_role_rewards(config.role_rewards, guild), inline=False)
    embed.add_field(name="💰 喵币发放", value=summarize_money_reward(config.money_reward), inline=False)
    embed.add_field(name="📈 股份发放", value=summarize_stock_rewards(config.stock_rewards), inline=False)
    if editor_name:
        embed.set_footer(text=f"最后编辑：{editor_name}")
    else:
        embed.set_footer(text="每位已注册喵喵仅限领取一次，福利类型可叠加发放")
    return embed


def has_any_welfare(config: WelfareConfig):
    return bool(config.role_rewards or config.stock_rewards or config.money_reward.get("enabled"))


def roll_money_reward(config: dict):
    if config.get("mode") == "fixed":
        return config["fixed_amount"], "定额档"

    min_amount = int(config["min_amount"])
    max_amount = int(config["max_amount"])
    if min_amount >= max_amount:
        return min_amount, "定额档"

    tier_label, _weight, ratio_start, ratio_end = random.choices(
        MONEY_TIER_WEIGHTS,
        weights=[item[1] for item in MONEY_TIER_WEIGHTS],
        k=1,
    )[0]
    total_span = max_amount - min_amount + 1
    start = min_amount + int(total_span * ratio_start)
    end = min_amount + int(total_span * ratio_end) - 1
    start = max(min_amount, min(start, max_amount))
    end = max(start, min(end, max_amount))
    return random.randint(start, end), tier_label


class WelfareContentModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="编辑福利公告")
        self.parent_view = parent_view
        self.add_item(InputText(label="公告标题", value=parent_view.config.title, max_length=100))
        self.add_item(
            InputText(
                label="公告内容",
                style=discord.InputTextStyle.long,
                value=parent_view.config.body,
                max_length=1500,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.config.title = self.children[0].value.strip() or self.parent_view.config.title
        self.parent_view.config.body = self.children[1].value.strip() or self.parent_view.config.body
        await self.parent_view.sync_message(interaction)
        await interaction.response.send_message("✅ 福利公告标题与内容已更新。", ephemeral=True)


class WelfareRoleModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="配置身份组抽选")
        self.parent_view = parent_view
        current = "\n".join(f"{item['role_id']}:{item['weight']}" for item in parent_view.config.role_rewards)
        self.add_item(
            InputText(
                label="每行填写 身份组ID:权重",
                style=discord.InputTextStyle.long,
                value=current,
                placeholder="例如：\n1521848592476668005:60\n123456789012345678:15",
                max_length=1000,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            self.parent_view.config.role_rewards = parse_role_rewards(self.children[0].value)
        except Exception as exc:
            return await interaction.response.send_message(f"🚫 身份组配置格式错误：{exc}", ephemeral=True)
        await self.parent_view.sync_message(interaction)
        await interaction.response.send_message("✅ 身份组抽选配置已更新。", ephemeral=True)


class WelfareMoneyModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="配置喵币福利")
        self.parent_view = parent_view
        current_mode = parent_view.config.money_reward.get("mode", "off") if parent_view.config.money_reward.get("enabled") else "off"
        if current_mode == "fixed":
            current_value = str(parent_view.config.money_reward.get("fixed_amount", 0))
        elif current_mode == "range":
            current_value = f"{parent_view.config.money_reward.get('min_amount', 0)}-{parent_view.config.money_reward.get('max_amount', 0)}"
        else:
            current_value = ""
        self.add_item(InputText(label="模式", value=current_mode, placeholder="off / fixed / range", max_length=20))
        self.add_item(
            InputText(
                label="数值",
                value=current_value,
                placeholder="fixed 填 50000；range 填 1000-999999",
                max_length=100,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            self.parent_view.config.money_reward = parse_money_reward(self.children[0].value, self.children[1].value)
        except Exception as exc:
            return await interaction.response.send_message(f"🚫 喵币配置格式错误：{exc}", ephemeral=True)
        await self.parent_view.sync_message(interaction)
        await interaction.response.send_message("✅ 喵币福利配置已更新。", ephemeral=True)


class WelfareStockModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="配置股份福利")
        self.parent_view = parent_view
        current = "\n".join(f"{item['stock_id']}:{item['quantity']}" for item in parent_view.config.stock_rewards)
        self.add_item(
            InputText(
                label="每行填写 股票ID:数量",
                style=discord.InputTextStyle.long,
                value=current,
                placeholder="例如：\nFISH:50\nDOGE:100",
                max_length=1000,
                required=False,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            self.parent_view.config.stock_rewards = parse_stock_rewards(self.children[0].value)
        except Exception as exc:
            return await interaction.response.send_message(f"🚫 股份配置格式错误：{exc}", ephemeral=True)
        await self.parent_view.sync_message(interaction)
        await interaction.response.send_message("✅ 股份福利配置已更新。", ephemeral=True)


class WelfareClaimView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="领取福利", style=discord.ButtonStyle.success, emoji="🎁", custom_id="town_welfare_claim")
    async def claim_btn(self, button, interaction: discord.Interaction):
        user = await get_citizen(interaction.user.id)
        if not user:
            return await interaction.response.send_message("🚫 仅限已注册喵喵领取，请先使用 `/喵喵小镇 注册`。", ephemeral=True)

        message = interaction.message
        if message is None:
            return await interaction.response.send_message("🚫 未找到福利消息。", ephemeral=True)

        welfare = await get_welfare_message(message.id)
        if welfare is None:
            return await interaction.response.send_message("🚫 这条福利消息尚未完成配置。", ephemeral=True)

        claim_status = await has_claimed_welfare(message.id, interaction.user.id)
        if claim_status == "claimed":
            return await interaction.response.send_message("你已经领取过这次福利了。", ephemeral=True)
        if claim_status == "pending":
            return await interaction.response.send_message("你的福利正在处理中，请稍后再试。", ephemeral=True)

        config = WelfareConfig(
            title=welfare["title"],
            body=welfare["body"],
            mention_registered_role=welfare["mention_enabled"],
            role_rewards=welfare["role_rewards"],
            money_reward=welfare["money_reward"],
            stock_rewards=welfare["stock_rewards"],
        )
        if not has_any_welfare(config):
            return await interaction.response.send_message("🚫 当前福利内容为空，暂时无法领取。", ephemeral=True)

        started = await begin_welfare_claim(message.id, interaction.user.id)
        if not started:
            return await interaction.response.send_message("你已经领取过这次福利了。", ephemeral=True)

        reward_lines = []
        payload = {"roles": [], "money": None, "stocks": []}
        try:
            if config.role_rewards:
                role_entry = random.choices(config.role_rewards, weights=[item["weight"] for item in config.role_rewards], k=1)[0]
                role_id = int(role_entry["role_id"])
                role = interaction.guild.get_role(role_id) if interaction.guild else None
                if role is None:
                    raise ValueError(f"未找到身份组 {role_id}")
                granted = await grant_role_by_id(
                    interaction.user,
                    interaction.guild,
                    role_id,
                    reason=f"福利发放领取，消息 {message.id}",
                )
                if not granted:
                    raise ValueError(f"身份组 {role.name} 发放失败")
                payload["roles"].append(role_id)
                reward_lines.append(f"🎭 获得身份组：**{role.name}**")

            if config.money_reward.get("enabled"):
                money_amount, tier_label = roll_money_reward(config.money_reward)
                await update_money(interaction.user.id, money_amount)
                payload["money"] = {"amount": money_amount, "tier": tier_label}
                reward_lines.append(f"💰 获得喵币：**{money_amount}**（{tier_label}）")

            for stock_entry in config.stock_rewards:
                stock_id = stock_entry["stock_id"]
                quantity = int(stock_entry["quantity"])
                await grant_stock_shares(interaction.user.id, stock_id, quantity)
                payload["stocks"].append({"stock_id": stock_id, "quantity": quantity})
                reward_lines.append(f"📈 获得股份：**{STOCKS[stock_id]['name']}** x **{quantity}** 股")

            await finish_welfare_claim(message.id, interaction.user.id, payload)
        except Exception as exc:
            await cancel_welfare_claim(message.id, interaction.user.id)
            return await interaction.response.send_message(f"🚫 福利发放失败：{exc}", ephemeral=True)

        await interaction.response.send_message("✅ 福利领取成功！\n" + "\n".join(reward_lines), ephemeral=True)


class WelfareConfigView(View):
    def __init__(self, target_message: discord.Message, config: WelfareConfig):
        super().__init__(timeout=1800)
        self.target_message = target_message
        self.config = config

    def build_panel_embed(self):
        embed = build_welfare_embed(self.config, self.target_message.guild if self.target_message else None)
        mention_status = "开启" if self.config.mention_registered_role else "关闭"
        embed.add_field(name="📣 发布设置", value=f"艾特喵喵镇民：**{mention_status}**", inline=False)
        return embed

    async def sync_message(self, interaction: discord.Interaction | None = None):
        content = None
        if self.config.mention_registered_role:
            role = self.target_message.guild.get_role(REGISTERED_ROLE_ID) if self.target_message.guild else None
            if role is not None:
                content = role.mention
        await self.target_message.edit(
            content=content,
            embed=build_welfare_embed(
                self.config,
                self.target_message.guild if self.target_message else None,
                editor_name=interaction.user.display_name if interaction else None,
            ),
            view=WelfareClaimView(),
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        await upsert_welfare_message(
            message_id=self.target_message.id,
            channel_id=self.target_message.channel.id,
            title=self.config.title,
            body=self.config.body,
            mention_enabled=self.config.mention_registered_role,
            mention_content=content or "",
            role_rewards=self.config.role_rewards,
            money_reward=self.config.money_reward,
            stock_rewards=self.config.stock_rewards,
        )

    @discord.ui.button(label="编辑标题内容", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_content_btn(self, button, interaction):
        await interaction.response.send_modal(WelfareContentModal(self))

    @discord.ui.button(label="切换艾特镇民", style=discord.ButtonStyle.secondary, emoji="📣", row=0)
    async def toggle_mention_btn(self, button, interaction):
        self.config.mention_registered_role = not self.config.mention_registered_role
        await self.sync_message(interaction)
        await interaction.response.edit_message(embed=self.build_panel_embed(), view=self)

    @discord.ui.button(label="身份组抽选", style=discord.ButtonStyle.primary, emoji="🎭", row=1)
    async def role_btn(self, button, interaction):
        await interaction.response.send_modal(WelfareRoleModal(self))

    @discord.ui.button(label="喵币发放", style=discord.ButtonStyle.success, emoji="💰", row=1)
    async def money_btn(self, button, interaction):
        await interaction.response.send_modal(WelfareMoneyModal(self))

    @discord.ui.button(label="股份发放", style=discord.ButtonStyle.primary, emoji="📈", row=1)
    async def stock_btn(self, button, interaction):
        await interaction.response.send_modal(WelfareStockModal(self))

    @discord.ui.button(label="查看预览", style=discord.ButtonStyle.secondary, emoji="👀", row=2)
    async def preview_btn(self, button, interaction):
        await interaction.response.send_message(embed=build_welfare_embed(self.config, interaction.guild), ephemeral=True)

    @discord.ui.button(label="同步到福利消息", style=discord.ButtonStyle.success, emoji="✅", row=2)
    async def sync_btn(self, button, interaction):
        await self.sync_message(interaction)
        await interaction.response.send_message("✅ 福利消息已同步更新。", ephemeral=True)


class Welfare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.claim_view = None
        self._view_registered = False

    async def ensure_claim_view_registered(self):
        if self._view_registered:
            return
        if self.claim_view is None:
            self.claim_view = WelfareClaimView()
        self.bot.add_view(self.claim_view)
        self._view_registered = True

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_claim_view_registered()

    @TOWN_GROUP.command(name="福利发放", description="【仅限管理员】发送一条可配置的福利领取公告")
    @commands.is_owner()
    async def welfare_drop(
        self,
        ctx: discord.ApplicationContext,
        是否艾特镇民: discord.Option(bool, "是否艾特喵喵镇民身份组", default=False),
        目标频道: discord.Option(discord.TextChannel, "要发送到的频道，默认当前频道", required=False, default=None),
    ):
        await self.ensure_claim_view_registered()
        await ctx.defer(ephemeral=True)
        target_channel = 目标频道 or ctx.channel
        if target_channel is None:
            return await ctx.followup.send("🚫 未找到可发送福利的目标频道。", ephemeral=True)

        config = WelfareConfig(mention_registered_role=是否艾特镇民)
        content = None
        if 是否艾特镇民:
            role = ctx.guild.get_role(REGISTERED_ROLE_ID) if ctx.guild else None
            if role is not None:
                content = role.mention

        target_message = await target_channel.send(
            content=content,
            embed=build_welfare_embed(config, ctx.guild, editor_name=ctx.author.display_name),
            view=WelfareClaimView(),
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        await upsert_welfare_message(
            message_id=target_message.id,
            channel_id=target_message.channel.id,
            title=config.title,
            body=config.body,
            mention_enabled=config.mention_registered_role,
            mention_content=content or "",
            role_rewards=config.role_rewards,
            money_reward=config.money_reward,
            stock_rewards=config.stock_rewards,
        )

        view = WelfareConfigView(target_message, config)
        await ctx.followup.send(
            f"✅ 福利公告已发送到 {target_channel.mention}。\n现在可以继续配置身份组抽选、喵币发放和股份福利。",
            embed=view.build_panel_embed(),
            view=view,
            ephemeral=True,
        )


def setup(bot):
    bot.add_cog(Welfare(bot))
