import asyncio
import datetime
import random
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from discord.ui import View

from app.db.repositories.daily_repo import (
    count_daily_signins_by_date,
    get_daily_signin,
    record_daily_signin,
)
from app.db.repositories.farm_repo import get_farm_guard, get_farm_state, plant_seed, set_farm_guard
from app.db.repositories.inventory_repo import add_item
from app.db.repositories.stock_repo import grant_stock_shares
from app.db.repositories.title_repo import check_title_owned, unlock_title
from app.db.repositories.user_repo import get_citizen, update_money
from app.shared.data.farm_data import FARM_GUARDS, PLANTS
from app.shared.data.shop_data import SHOP_ITEMS
from app.shared.data.stock_data import STOCKS
from app.shared.data.title_data import TITLES

SIGNIN_CHANNEL_ID = 1443488941045977140
CHECKIN_TITLE = "🌞 喵喵镇民每日签到"
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
SIGNIN_PANEL_ID = "daily_signin_panel_v1"


def get_beijing_now():
    return datetime.datetime.now(BEIJING_TZ)


def get_beijing_date_str():
    return get_beijing_now().strftime("%Y-%m-%d")


def build_bonus_pool():
    return [
        ("money", 30),
        ("stock", 18),
        ("fertilizer", 18),
        ("title", 8),
        ("guard", 12),
        ("seed", 14),
    ]


async def build_checkin_embed():
    today = get_beijing_date_str()
    today_count = await count_daily_signins_by_date(today)
    now_text = get_beijing_now().strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(title=CHECKIN_TITLE, color=0xF1C40F, url=f"https://panel.local/{SIGNIN_PANEL_ID}")
    embed.description = (
        "欢迎来到镇民签到站。\n"
        "已注册喵喵每天都可以来签到一次，按 **北京时间** 结算。"
    )
    embed.add_field(name="基础奖励", value="随机获得 **1000 - 99999999** 喵币。", inline=False)
    embed.add_field(
        name="附加惊喜",
        value="偶尔会触发股市、农场、称号联动奖励，例如股票、化肥、种子、护卫、稀有称号等。",
        inline=False,
    )
    embed.add_field(name="今日签到人数", value=f"**{today_count}** 位镇民", inline=True)
    embed.add_field(name="当前日期", value=f"**{today}**", inline=True)
    embed.set_footer(text=f"最后刷新: {now_text} | 每日 0 点后可再次签到（北京时间） | 面板ID:{SIGNIN_PANEL_ID}")
    return embed


def is_signin_panel_message(message: discord.Message):
    if message.author.bot is False or not message.embeds:
        return False
    embed = message.embeds[0]
    return embed.title == CHECKIN_TITLE and (embed.url or "").endswith(SIGNIN_PANEL_ID)


async def apply_bonus_event(user_id):
    event_type = random.choices(
        [item[0] for item in build_bonus_pool()],
        [item[1] for item in build_bonus_pool()],
        k=1,
    )[0]

    if event_type == "money":
        extra = random.randint(1000, 500000)
        await update_money(user_id, extra)
        return f"💰 附加事件：额外获得 **{extra}** 喵币。"

    if event_type == "stock":
        stock_id = random.choice(list(STOCKS.keys()))
        quantity = random.randint(5, 50)
        await grant_stock_shares(user_id, stock_id, quantity)
        return f"📈 附加事件：获得 **{STOCKS[stock_id]['name']} ({stock_id})** **{quantity}** 股。"

    if event_type == "fertilizer":
        item_name = random.choice([name for name, item in SHOP_ITEMS.items() if item["type"] == "farm"])
        quantity = random.randint(1, 5)
        await add_item(user_id, item_name, quantity)
        return f"🧪 附加事件：获得 **{item_name} x{quantity}**。"

    if event_type == "title":
        rare_ids = [tid for tid, data in TITLES.items() if data["rarity"] in {"R", "SR", "SSR"}]
        random.shuffle(rare_ids)
        for title_id in rare_ids:
            if not await check_title_owned(user_id, title_id):
                await unlock_title(user_id, title_id)
                return f"👑 附加事件：解锁稀有称号 **【{TITLES[title_id]['name']}】**。"
        fallback = random.randint(5000, 50000)
        await update_money(user_id, fallback)
        return f"👑 附加事件：称号库里你运气太好了都快拿满了，改为补发 **{fallback}** 喵币。"

    if event_type == "guard":
        guard_type = random.choice(list(FARM_GUARDS.keys()))
        guard = FARM_GUARDS[guard_type]
        bonus_hours = max(6, guard["duration_hours"] // 2)
        current_time = int(datetime.datetime.now().timestamp())
        current_guard = await get_farm_guard(user_id, current_time=current_time)
        expires_at = current_time + bonus_hours * 3600
        if current_guard:
            _current_type, current_expires_at = current_guard
            expires_at = max(expires_at, current_expires_at)
        await set_farm_guard(user_id, guard_type, expires_at)
        return f"🛡️ 附加事件：免费获得 **{guard['name']}** 守卫，持续约 **{bonus_hours}** 小时。"

    if event_type == "seed":
        candidate_ids = [pid for pid, data in PLANTS.items() if data["rarity"] in {"N", "R"}]
        plant_id = random.choice(candidate_ids)
        plant = PLANTS[plant_id]
        plots = await get_farm_state(user_id)
        empty_plots = [row[1] for row in plots if row[2] is None]
        if empty_plots:
            await plant_seed(user_id, empty_plots[0], plant_id, int(datetime.datetime.now().timestamp()))
            return f"🌱 附加事件：系统赠送了一株 **{plant['name']}** 并帮你种在了空地上。"
        fallback = plant["cost"] * 3
        await update_money(user_id, fallback)
        return f"🌱 附加事件：原本想送你 **{plant['name']}**，但农场没空地了，改发 **{fallback}** 喵币。"

    return None


class DailySigninView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="每日签到",
        style=discord.ButtonStyle.success,
        emoji="📅",
        custom_id="daily_signin_claim_button",
    )
    async def signin_btn(self, button, interaction):
        user = await get_citizen(interaction.user.id)
        if not user:
            return await interaction.response.send_message(
                "🚫 仅限已注册喵喵签到，请先使用 `/喵喵小镇 注册`。",
                ephemeral=True,
            )

        today = get_beijing_date_str()
        row = await get_daily_signin(interaction.user.id)
        if row and row[1] == today:
            return await interaction.response.send_message("📌 你今天已经签到过了，明天再来吧。", ephemeral=True)

        base_reward = random.randint(1000, 99999999)
        await update_money(interaction.user.id, base_reward)
        await record_daily_signin(interaction.user.id, today, base_reward)

        bonus_message = None
        if random.random() < 0.35:
            bonus_message = await apply_bonus_event(interaction.user.id)

        embed = discord.Embed(title="✅ 签到成功", color=0x2ECC71)
        embed.description = f"你今天的基础签到奖励是 **{base_reward}** 喵币。"
        if bonus_message:
            embed.add_field(name="幸运附加事件", value=bonus_message, inline=False)
        embed.set_footer(text=f"签到日期：{today}（北京时间）")

        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            if interaction.message:
                await interaction.message.edit(embed=await build_checkin_embed(), view=self)
        except Exception:
            pass

        asyncio.create_task(self.cog.ensure_panel_bottom())


class DailySignin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.panel_lock = None
        self.panel_view = None
        self.runtime_ready = False

    def cog_unload(self):
        if self.panel_maintainer.is_running():
            self.panel_maintainer.cancel()

    async def ensure_runtime_ready(self):
        if self.runtime_ready:
            return
        self.panel_lock = self.panel_lock or asyncio.Lock()
        self.panel_view = self.panel_view or DailySigninView(self)
        self.bot.add_view(self.panel_view)
        if not self.panel_maintainer.is_running():
            self.panel_maintainer.start()
        self.runtime_ready = True

    async def find_panel_messages(self, channel):
        panel_messages = []
        async for message in channel.history(limit=100):
            if is_signin_panel_message(message):
                panel_messages.append(message)
        return panel_messages

    async def get_latest_panel_message(self, channel=None):
        channel = channel or self.bot.get_channel(SIGNIN_CHANNEL_ID)
        if channel is None:
            return None
        panel_messages = await self.find_panel_messages(channel)
        return panel_messages[0] if panel_messages else None

    async def ensure_panel_bottom(self):
        if self.panel_lock is None or self.panel_view is None:
            await self.ensure_runtime_ready()
        async with self.panel_lock:
            channel = self.bot.get_channel(SIGNIN_CHANNEL_ID)
            if channel is None:
                return

            stock_cog = self.bot.get_cog("StockMarket")
            if stock_cog is not None:
                await stock_cog.ensure_news_panel_stack_bottom(channel=channel)

            panel_messages = await self.find_panel_messages(channel)
            newest_panel = panel_messages[0] if panel_messages else None
            latest_message = None
            async for message in channel.history(limit=1):
                latest_message = message

            stock_panel = None
            if stock_cog is not None:
                stock_panel = await stock_cog.find_stock_panel_messages(channel)
                stock_panel = stock_panel[0] if stock_panel else None

            need_new_panel = (
                newest_panel is None
                or latest_message is None
                or latest_message.id != newest_panel.id
                or (stock_panel is not None and newest_panel.id < stock_panel.id)
            )
            new_panel_message = newest_panel
            if need_new_panel:
                new_panel_message = await channel.send(embed=await build_checkin_embed(), view=self.panel_view)

            for message in panel_messages:
                if new_panel_message and message.id != new_panel_message.id:
                    try:
                        await message.delete()
                    except Exception:
                        pass

            if new_panel_message and not need_new_panel:
                try:
                    await new_panel_message.edit(embed=await build_checkin_embed(), view=self.panel_view)
                except Exception:
                    pass

    async def force_send_panel(self):
        if self.panel_lock is None or self.panel_view is None:
            await self.ensure_runtime_ready()
        async with self.panel_lock:
            channel = self.bot.get_channel(SIGNIN_CHANNEL_ID)
            if channel is None:
                return None

            panel_messages = await self.find_panel_messages(channel)
            new_panel_message = await channel.send(embed=await build_checkin_embed(), view=self.panel_view)

            for message in panel_messages:
                try:
                    await message.delete()
                except Exception:
                    pass

            return new_panel_message

    @tasks.loop(minutes=10)
    async def panel_maintainer(self):
        await self.ensure_panel_bottom()

    @panel_maintainer.before_loop
    async def before_panel_maintainer(self):
        await self.bot.wait_until_ready()
        db_ready_event = getattr(self.bot, "db_ready_event", None)
        if db_ready_event is not None:
            await db_ready_event.wait()
        await asyncio.sleep(3)

    @commands.Cog.listener()
    async def on_ready(self):
        db_ready_event = getattr(self.bot, "db_ready_event", None)
        if db_ready_event is not None:
            await db_ready_event.wait()
        await self.ensure_runtime_ready()
        await self.ensure_panel_bottom()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id != SIGNIN_CHANNEL_ID:
            return
        await self.ensure_panel_bottom()


def setup(bot):
    bot.add_cog(DailySignin(bot))
