import random
import re
from dataclasses import dataclass, field

import discord
from discord.ext import commands
from discord.ui import InputText, Modal, View

from app.cogs.gameplay.cat import TOWN_GROUP, register_town_group_command
from app.db.repositories.stock_repo import grant_stock_shares
from app.db.repositories.user_repo import get_citizen, update_money
from app.db.repositories.welfare_repo import (
    begin_welfare_claim,
    cancel_welfare_claim,
    count_claimed_welfare_users,
    finish_welfare_claim,
    get_all_role_notice_claims,
    get_welfare_message,
    get_pending_role_notice_claims,
    has_claimed_welfare,
    mark_role_notice_sent,
    upsert_welfare_message,
)
from app.shared.data.stock_data import STOCKS
from app.shared.discord_roles import REGISTERED_ROLE_ID, grant_role_by_id

WELFARE_ROLE_NOTICE_CHANNEL_ID = 1426616953975607476
WELFARE_ROLE_NOTICE_MARKER = "[WELFARE_ROLE_NOTICE_V2]"
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


def build_welfare_embed(
    config: WelfareConfig,
    guild: discord.Guild | None = None,
    *,
    editor_name: str | None = None,
    claimed_count: int = 0,
):
    embed = discord.Embed(title=config.title, description=config.body, color=0xF39C12)
    embed.add_field(name="🎭 身份组抽选", value=summarize_role_rewards(config.role_rewards, guild), inline=False)
    embed.add_field(name="💰 喵币发放", value=summarize_money_reward(config.money_reward), inline=False)
    embed.add_field(name="📈 股份发放", value=summarize_stock_rewards(config.stock_rewards), inline=False)
    embed.add_field(name="📊 领取喵喵统计", value=f"已领取：**{claimed_count}** 只喵喵", inline=False)
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


async def send_welfare_role_notice(bot, claim: dict):
    channel = bot.get_channel(WELFARE_ROLE_NOTICE_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(WELFARE_ROLE_NOTICE_CHANNEL_ID)
        except Exception:
            return False

    guild = getattr(channel, "guild", None)
    user = guild.get_member(claim["user_id"]) if guild else None
    if user is None:
        user = bot.get_user(claim["user_id"])
    if user is None:
        try:
            user = await bot.fetch_user(claim["user_id"])
        except Exception:
            user = None

    payload = claim["payload"]
    role_ids = payload.get("roles") or []
    if not role_ids:
        return True

    role_mentions = []
    for role_id in role_ids:
        role = guild.get_role(int(role_id)) if guild else None
        role_mentions.append(role.mention if role else f"<@&{role_id}>")

    user_name = user.display_name if user and hasattr(user, "display_name") else (user.name if user else f"用户 {claim['user_id']}")
    record_key = f"WELFARE_ROLE_NOTICE|{claim['message_id']}|{claim['user_id']}|{claim.get('claimed_at', 'unknown')}"
    await channel.send(
        "\n".join(
            [
                f"{WELFARE_ROLE_NOTICE_MARKER} 福利身份组领取记录",
                f"领取用户：<@{claim['user_id']}> (`{claim['user_id']}`) / {user_name}",
                f"获得身份组：{'、'.join(role_mentions)}",
                f"特殊标记：`{record_key}`",
            ]
        ),
        allowed_mentions=discord.AllowedMentions(users=True, roles=True),
    )
    return True


def is_welfare_role_notice_message(message: discord.Message, bot_user_id: int | None):
    if bot_user_id is not None and message.author.id != bot_user_id:
        return False
    content = message.content or ""
    return WELFARE_ROLE_NOTICE_MARKER in content or "领取福利获得身份组" in content or "福利身份组领取记录" in content


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
        await self.parent_view.refresh_panel_message()
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
        await self.parent_view.refresh_panel_message()
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
        await self.parent_view.refresh_panel_message()
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
        await self.parent_view.refresh_panel_message()
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

        welfare_cog = interaction.client.get_cog("Welfare")
        if welfare_cog is not None and payload["roles"]:
            sent = await send_welfare_role_notice(
                interaction.client,
                {
                    "message_id": message.id,
                    "user_id": interaction.user.id,
                    "payload": payload,
                },
            )
            if sent:
                await mark_role_notice_sent(message.id, interaction.user.id)

        claimed_count = await count_claimed_welfare_users(message.id)
        try:
            await message.edit(
                embed=build_welfare_embed(config, interaction.guild, claimed_count=claimed_count),
                view=WelfareClaimView(),
            )
        except discord.HTTPException:
            pass

        await interaction.response.send_message("✅ 福利领取成功！\n" + "\n".join(reward_lines), ephemeral=True)


class WelfareConfigView(View):
    def __init__(self, target_channel: discord.abc.Messageable, config: WelfareConfig):
        super().__init__(timeout=1800)
        self.target_channel = target_channel
        self.target_message = None
        self.panel_message = None
        self.config = config
        self._claimed_count = 0

    def build_panel_embed(self):
        guild = self.target_message.guild if self.target_message else getattr(self.target_channel, "guild", None)
        embed = build_welfare_embed(self.config, guild, claimed_count=self.claimed_count)
        mention_status = "开启" if self.config.mention_registered_role else "关闭"
        embed.add_field(name="📣 发布设置", value=f"艾特喵喵镇民：**{mention_status}**", inline=False)
        embed.add_field(
            name="正式发布状态",
            value="已发布，可继续同步更新" if self.target_message else "未发布，确认后才会发送到频道",
            inline=False,
        )
        return embed

    @property
    def claimed_count(self):
        if self.target_message is None:
            return 0
        return getattr(self, "_claimed_count", 0)

    async def refresh_claimed_count(self):
        if self.target_message is None:
            self._claimed_count = 0
            return
        self._claimed_count = await count_claimed_welfare_users(self.target_message.id)

    async def refresh_panel_message(self):
        if self.panel_message is None:
            return
        try:
            await self.panel_message.edit(embed=self.build_panel_embed(), view=self)
        except discord.HTTPException:
            pass

    async def sync_message(self, interaction: discord.Interaction | None = None):
        if self.target_message is None:
            return
        await self.refresh_claimed_count()
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
                claimed_count=self.claimed_count,
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
        await self.refresh_panel_message()

    async def publish_message(self, interaction: discord.Interaction):
        content = None
        guild = getattr(self.target_channel, "guild", None)
        if self.config.mention_registered_role:
            role = guild.get_role(REGISTERED_ROLE_ID) if guild else None
            if role is not None:
                content = role.mention

        if self.target_message is None:
            self.target_message = await self.target_channel.send(
                content=content,
                embed=build_welfare_embed(
                    self.config,
                    guild,
                    editor_name=interaction.user.display_name,
                    claimed_count=0,
                ),
                view=WelfareClaimView(),
                allowed_mentions=discord.AllowedMentions(roles=True),
            )
        else:
            await self.sync_message(interaction)

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
        await self.refresh_panel_message()

    @discord.ui.button(label="编辑标题内容", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_content_btn(self, button, interaction):
        await interaction.response.send_modal(WelfareContentModal(self))

    @discord.ui.button(label="切换艾特镇民", style=discord.ButtonStyle.secondary, emoji="📣", row=0)
    async def toggle_mention_btn(self, button, interaction):
        self.config.mention_registered_role = not self.config.mention_registered_role
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
        content = None
        if self.config.mention_registered_role:
            role = interaction.guild.get_role(REGISTERED_ROLE_ID) if interaction.guild else None
            if role is not None:
                content = role.mention
        preview_count = 0
        if self.target_message is not None:
            preview_count = await count_claimed_welfare_users(self.target_message.id)
        await interaction.response.send_message(
            content=content,
            embed=build_welfare_embed(self.config, interaction.guild, claimed_count=preview_count),
            view=WelfareClaimView(),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )

    @discord.ui.button(label="确认发布", style=discord.ButtonStyle.success, emoji="✅", row=2)
    async def publish_btn(self, button, interaction):
        await self.publish_message(interaction)
        if self.target_message is None:
            return
        await interaction.response.send_message(
            f"✅ 福利正式面板已发布到 {self.target_channel.mention}。",
            ephemeral=True,
        )


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

    async def backfill_role_notices(self):
        claims = await get_pending_role_notice_claims()
        for claim in claims:
            sent = await send_welfare_role_notice(self.bot, claim)
            if sent:
                await mark_role_notice_sent(claim["message_id"], claim["user_id"])

    async def rebuild_role_notice_channel(self):
        channel = self.bot.get_channel(WELFARE_ROLE_NOTICE_CHANNEL_ID)
        if channel is None:
            channel = await self.bot.fetch_channel(WELFARE_ROLE_NOTICE_CHANNEL_ID)

        deleted = 0
        bot_user_id = self.bot.user.id if self.bot.user else None
        async for message in channel.history(limit=None):
            if not is_welfare_role_notice_message(message, bot_user_id):
                continue
            try:
                await message.delete()
                deleted += 1
            except discord.HTTPException:
                pass

        claims = await get_all_role_notice_claims()
        resent = 0
        for claim in claims:
            sent = await send_welfare_role_notice(self.bot, claim)
            if sent:
                resent += 1
        return deleted, resent, len(claims)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_claim_view_registered()
        await self.backfill_role_notices()

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
        view = WelfareConfigView(target_channel, config)
        panel_message = await ctx.followup.send(
            f"✅ 已打开福利配置面板，目标频道为 {target_channel.mention}。\n先在这里配置并预览，确认无误后再发布正式福利面板。",
            embed=view.build_panel_embed(),
            view=view,
            ephemeral=True,
            wait=True,
        )
        view.panel_message = panel_message

    @TOWN_GROUP.command(name="重建福利播报", description="【仅限管理员】清空福利领取播报并按新格式重发")
    @commands.is_owner()
    async def rebuild_welfare_role_notices(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        try:
            deleted, resent, total = await self.rebuild_role_notice_channel()
        except Exception as exc:
            return await ctx.followup.send(f"🚫 重建福利播报失败：{exc}", ephemeral=True)

        await ctx.followup.send(
            f"✅ 福利领取播报已重建。\n已清理旧播报：**{deleted}** 条\n数据库内可重发记录：**{total}** 条\n实际重发：**{resent}** 条",
            ephemeral=True,
        )


def setup(bot):
    register_town_group_command(bot, Welfare.welfare_drop)
    register_town_group_command(bot, Welfare.rebuild_welfare_role_notices)
    bot.add_cog(Welfare(bot))
