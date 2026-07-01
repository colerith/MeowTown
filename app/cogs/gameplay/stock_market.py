import asyncio
import datetime
import os
from dataclasses import dataclass

import discord
from discord.ext import commands, tasks
from discord.ui import Button, InputText, Modal, Select, View

from app.db.repositories.stock_repo import (
    borrow_money,
    buy_stock,
    claim_stock_compensation,
    get_loan_amount,
    get_portfolio_with_prices,
    get_stock_price,
    has_claimed_stock_compensation,
    initialize_stocks,
    list_market_stocks,
    repay_loan,
    reset_stock_market,
    sell_stock,
    update_stock_quote,
)
from app.db.repositories.user_repo import get_citizen, get_user_money, list_registered_user_ids
from app.features.stock_market.service import (
    format_market_trend,
    parse_positive_amount,
    parse_positive_int,
    summarize_portfolio,
)
from app.shared.data.stock_data import STOCKS, calculate_next_price, generate_dynamic_news

NEWS_CHANNEL_ID = 1443488941045977140
REGISTERED_ROLE_ID = 1521848592476668005
COMPENSATION_STOCK_OPTIONS = ("FISH", "CATN", "TOY", "BOX")
COMPENSATION_SHARES_PER_STOCK = 100
IMG_STOCK = "https://i.postimg.cc/gcSBzV0j/stock-market.png"
STOCK_NEWS_TITLE = "📈 喵尔街快讯"
STOCK_NEWS_PANEL_ID = "stock_news_panel_v1"


def get_guide_embed():
    embed = discord.Embed(title="📈 喵尔街风云 · 投资指南", color=0xFFD700)
    embed.description = "欢迎来到喵喵小镇的金融中心！在这里，你可以一夜暴富，也可能天台排队。"
    embed.add_field(
        name="🏢 上市公司简介",
        value=(
            "🐟 **咸鱼海运 (FISH)**: 价格亲民，波动小，避风港。\n"
            "📦 **纸箱地产 (BOX)**: 稳健增长，受天气影响。\n"
            "🎣 **逗猫棒重工 (TOY)**: 周期性波动，受消费新闻影响。\n"
            "🌿 **猫薄荷生物 (CATN)**: **高风险高回报**！研发成功暴涨。\n"
            "🐕 **柴犬币 (DOGE)**: **极度危险**！可能翻倍也可能归零。"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎮 核心玩法",
        value=(
            "**1. 市场刷新**: 每 **20分钟** 刷新一次价格和新闻。\n"
            "**2. 看新闻**: 新闻是价格的风向标！利好买入，利空卖出。\n"
            "**3. 操作**: 点击按钮即可买入/卖出，无需指令。"
        ),
        inline=False,
    )
    embed.add_field(
        name="☠️ 杠杆与破产",
        value=(
            "**🏦 融资**: 当前采用固定额度借款。\n"
            "**🚨 破产**: 后续会补充强制平仓与净资产清算逻辑。"
        ),
        inline=False,
    )
    embed.set_footer(text="投资有风险，入市需谨慎 | 祝各位喵老板发大财！")
    return embed


async def render_market_embed():
    embed = discord.Embed(title="📊 喵尔街实时行情", color=0x1ABC9C)
    embed.set_image(url=IMG_STOCK)

    rows = await list_market_stocks()
    if not rows:
        embed.description = "市场尚未开盘..."
        return embed

    for stock_id, price, change in rows:
        data = STOCKS.get(stock_id, {"icon": "❓", "name": "未知"})
        trend, pct = format_market_trend(price, change)
        embed.add_field(
            name=f"{data['icon']} {data['name']} ({stock_id})",
            value=f"Price: **{price:.2f}**\nTrend: {trend} ({pct:+.1f}%)",
            inline=True,
        )

    embed.set_footer(text="数据每20分钟刷新一次 | 投资有风险，入市需谨慎")
    return embed


def is_stock_news_message(message: discord.Message):
    if message.author.bot is False or not message.embeds:
        return False
    embed = message.embeds[0]
    return embed.title == STOCK_NEWS_TITLE and (embed.url or "").endswith(STOCK_NEWS_PANEL_ID)


async def build_stock_news_embed():
    news_embed = discord.Embed(title=STOCK_NEWS_TITLE, color=0x3498DB, url=f"https://panel.local/{STOCK_NEWS_PANEL_ID}")
    for stock_id, data in STOCKS.items():
        current_price = await get_stock_price(stock_id) or data["base_price"]
        news, score = generate_dynamic_news(stock_id, current_price=current_price)
        new_price, change_pct = calculate_next_price(stock_id, current_price, score)
        price_diff = round(new_price - current_price, 2)
        await update_stock_quote(stock_id, new_price, price_diff)

        if price_diff > 0:
            icon = "🔼"
        elif price_diff < 0:
            icon = "🔽"
        else:
            icon = "⏺️"

        news_embed.add_field(
            name=f"{data['icon']} {data['name']}",
            value=f"**{new_price:.2f}** {icon} ({change_pct:+.2f}%)\n> {news}",
            inline=False,
        )

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    news_embed.set_footer(text=f"最后刷新: {now_str} | 20分钟更新一次 | 面板ID:{STOCK_NEWS_PANEL_ID}")
    return news_embed, now_str


@dataclass
class CompensationAnnouncementConfig:
    title: str = "📢 喵尔街补偿公告"
    body: str = (
        "近期喵尔街快讯刷新异常、部分企业股价出现失真膨胀，给大家的交易体验带来了影响。\n\n"
        "我们已开始修复行情刷新与价格保护机制，并对股票数据执行重置处理。"
    )
    compensation_text: str = "已注册喵喵可免费领取 **2 个企业股票**，每个企业 **100 股**。"
    rules_text: str = (
        "1. 仅限已完成 `/市民 注册` 的喵喵领取\n"
        "2. 每位喵喵仅可领取一次\n"
        "3. 可选企业：咸鱼海运、猫薄荷生物、逗猫棒重工、纸箱地产"
    )
    note_text: str = "点击下方按钮后，选择两个不同企业即可立即入账。"
    mention_registered_role: bool = False


def build_compensation_embed(config: CompensationAnnouncementConfig | None = None):
    config = config or CompensationAnnouncementConfig()
    embed = discord.Embed(title=config.title, color=0xE67E22)
    embed.description = config.body
    embed.add_field(
        name="补偿内容",
        value=config.compensation_text,
        inline=False,
    )
    embed.add_field(
        name="领取规则",
        value=config.rules_text,
        inline=False,
    )
    embed.add_field(
        name="说明",
        value=config.note_text,
        inline=False,
    )
    embed.set_footer(text="感谢大家的理解与支持，喵尔街正在恢复秩序。")
    return embed


class CompensationContentModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="编辑公告标题与正文")
        self.parent_view = parent_view
        self.add_item(InputText(label="公告标题", value=parent_view.config.title, max_length=100))
        self.add_item(
            InputText(
                label="公告正文",
                style=discord.InputTextStyle.long,
                value=parent_view.config.body,
                max_length=1000,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.config.title = self.children[0].value.strip() or self.parent_view.config.title
        self.parent_view.config.body = self.children[1].value.strip() or self.parent_view.config.body
        if self.parent_view.message is not None:
            await self.parent_view.message.edit(embed=self.parent_view.build_preview_embed(), view=self.parent_view)
        await interaction.response.send_message("✅ 公告标题与正文已更新。", ephemeral=True)


class CompensationDetailModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="编辑补偿说明")
        self.parent_view = parent_view
        self.add_item(
            InputText(
                label="补偿内容",
                style=discord.InputTextStyle.long,
                value=parent_view.config.compensation_text,
                max_length=600,
            )
        )
        self.add_item(
            InputText(
                label="领取规则",
                style=discord.InputTextStyle.long,
                value=parent_view.config.rules_text,
                max_length=1000,
            )
        )
        self.add_item(
            InputText(
                label="补充说明",
                style=discord.InputTextStyle.long,
                value=parent_view.config.note_text,
                max_length=500,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.config.compensation_text = self.children[0].value.strip() or self.parent_view.config.compensation_text
        self.parent_view.config.rules_text = self.children[1].value.strip() or self.parent_view.config.rules_text
        self.parent_view.config.note_text = self.children[2].value.strip() or self.parent_view.config.note_text
        if self.parent_view.message is not None:
            await self.parent_view.message.edit(embed=self.parent_view.build_preview_embed(), view=self.parent_view)
        await interaction.response.send_message("✅ 补偿规则与说明已更新。", ephemeral=True)


class CompensationStockSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=f"{stock_id} - {STOCKS[stock_id]['name']}",
                value=stock_id,
                emoji=STOCKS[stock_id]["icon"],
            )
            for stock_id in COMPENSATION_STOCK_OPTIONS
        ]
        super().__init__(
            placeholder="选择两个企业股票",
            min_values=2,
            max_values=2,
            options=options,
            custom_id="stock_compensation_select",
        )

    async def callback(self, interaction: discord.Interaction):
        user = await get_citizen(interaction.user.id)
        if not user:
            return await interaction.response.send_message(
                "🚫 仅限已注册喵喵领取，请先使用 `/市民 注册`。",
                ephemeral=True,
            )

        if len(set(self.values)) != 2:
            return await interaction.response.send_message("请准确选择两个不同企业。", ephemeral=True)

        if await has_claimed_stock_compensation(interaction.user.id):
            return await interaction.response.send_message("你已经领取过这次补偿了。", ephemeral=True)

        success = await claim_stock_compensation(
            interaction.user.id,
            list(self.values),
            COMPENSATION_SHARES_PER_STOCK,
        )
        if not success:
            return await interaction.response.send_message("你已经领取过这次补偿了。", ephemeral=True)

        stock_names = "、".join(STOCKS[stock_id]["name"] for stock_id in self.values)
        await interaction.response.send_message(
            f"✅ 补偿发放完成！你已领取 **{stock_names}** 各 **{COMPENSATION_SHARES_PER_STOCK}** 股。",
            ephemeral=True,
        )


class CompensationClaimView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="领取股票补偿",
        style=discord.ButtonStyle.success,
        emoji="🎁",
        custom_id="stock_compensation_claim_button",
    )
    async def claim_btn(self, button, interaction):
        user = await get_citizen(interaction.user.id)
        if not user:
            return await interaction.response.send_message(
                "🚫 仅限已注册喵喵领取，请先使用 `/市民 注册`。",
                ephemeral=True,
            )

        if await has_claimed_stock_compensation(interaction.user.id):
            return await interaction.response.send_message("你已经领取过这次补偿了。", ephemeral=True)

        view = View(timeout=120)
        view.add_item(CompensationStockSelect())
        await interaction.response.send_message(
            "请选择两个不同企业股票，每个企业将补偿 100 股。",
            view=view,
            ephemeral=True,
        )


class CompensationConfigView(View):
    def __init__(self):
        super().__init__(timeout=900)
        self.config = CompensationAnnouncementConfig()
        self.message = None

    def build_preview_embed(self):
        embed = build_compensation_embed(self.config)
        mention_status = "开启" if self.config.mention_registered_role else "关闭"
        embed.add_field(name="发布设置", value=f"艾特喵喵镇民身份组：**{mention_status}**", inline=False)
        return embed

    @discord.ui.button(label="编辑标题正文", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_content_btn(self, button, interaction):
        self.message = interaction.message
        await interaction.response.send_modal(CompensationContentModal(self))

    @discord.ui.button(label="编辑补偿规则", style=discord.ButtonStyle.primary, emoji="🎁", row=0)
    async def edit_detail_btn(self, button, interaction):
        self.message = interaction.message
        await interaction.response.send_modal(CompensationDetailModal(self))

    @discord.ui.button(label="切换艾特镇民", style=discord.ButtonStyle.secondary, emoji="📣", row=0)
    async def toggle_mention_btn(self, button, interaction):
        self.config.mention_registered_role = not self.config.mention_registered_role
        self.message = interaction.message
        await interaction.response.edit_message(embed=self.build_preview_embed(), view=self)

    @discord.ui.button(label="预览公告", style=discord.ButtonStyle.secondary, emoji="👀", row=1)
    async def preview_btn(self, button, interaction):
        await interaction.response.send_message(embed=build_compensation_embed(self.config), ephemeral=True)

    @discord.ui.button(label="发布到频道", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def publish_btn(self, button, interaction):
        channel = interaction.client.get_channel(NEWS_CHANNEL_ID)
        if not channel:
            return await interaction.response.send_message("🚫 未找到目标频道，无法发布补偿公告。", ephemeral=True)

        content = None
        if self.config.mention_registered_role:
            role = interaction.guild.get_role(REGISTERED_ROLE_ID) if interaction.guild else None
            if role:
                content = role.mention

        await channel.send(
            content=content,
            embed=build_compensation_embed(self.config),
            view=CompensationClaimView(),
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        await interaction.response.send_message("✅ 补偿公告已发送到目标频道。", ephemeral=True)


async def create_stock_market_dashboard():
    return await render_market_embed(), StockDashboardView()


async def open_compensation_config_panel(interaction: discord.Interaction):
    view = CompensationConfigView()
    await interaction.response.send_message(embed=view.build_preview_embed(), view=view, ephemeral=True)


class TradeModal(Modal):
    def __init__(self, stock_id, action, current_price, user_id):
        super().__init__(title=f"{action} {stock_id}")
        self.stock_id = stock_id
        self.action = action
        self.price = current_price
        self.user_id = user_id
        self.add_item(InputText(label="数量", placeholder="请输入整数 (例如: 100)"))

    async def callback(self, interaction: discord.Interaction):
        try:
            amount = parse_positive_int(self.children[0].value)
        except Exception:
            return await interaction.response.send_message("❌ 请输入有效的正整数！", ephemeral=True)

        total_value = round(self.price * amount, 2)
        if self.action == "买入":
            success, balance = await buy_stock(self.user_id, self.stock_id, amount, self.price)
            if not success:
                return await interaction.response.send_message(
                    f"🚫 余额不足！需要 {total_value:.2f}，你有 {balance:.2f}。",
                    ephemeral=True,
                )
            message = (
                f"✅ 以 **{self.price:.2f}** 买入 **{amount}** 股 **{self.stock_id}**，"
                f"花费 **{total_value:.2f}** 喵币。"
            )
        else:
            success, owned_quantity = await sell_stock(self.user_id, self.stock_id, amount, self.price)
            if not success:
                return await interaction.response.send_message(
                    f"🚫 持仓不足！当前仅有 **{owned_quantity}** 股。",
                    ephemeral=True,
                )
            message = (
                f"✅ 以 **{self.price:.2f}** 卖出 **{amount}** 股 **{self.stock_id}**，"
                f"获得 **{total_value:.2f}** 喵币。"
            )

        await interaction.response.send_message(message, ephemeral=True)


class StockSelect(Select):
    def __init__(self, action, user_id):
        self.action_type = action
        self.user_id = user_id
        options = [
            discord.SelectOption(label=f"{sid} - {data['name']}", value=sid, emoji=data["icon"])
            for sid, data in STOCKS.items()
        ]
        super().__init__(placeholder=f"选择要{action}的股票...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        stock_id = self.values[0]
        current_price = await get_stock_price(stock_id)
        action_name = "买入" if self.action_type == "buy" else "卖出"
        await interaction.response.send_modal(TradeModal(stock_id, action_name, current_price, self.user_id))


class TradeView(View):
    def __init__(self, action, user_id):
        super().__init__(timeout=60)
        self.add_item(StockSelect(action, user_id))


class LoanModal(Modal):
    def __init__(self, user_id, action):
        super().__init__(title=f"{action}中心")
        self.user_id = user_id
        self.action = action
        self.add_item(InputText(label="金额", placeholder="请输入数字 (可带小数)"))

    async def callback(self, interaction: discord.Interaction):
        try:
            amount = parse_positive_amount(self.children[0].value)
        except Exception:
            return await interaction.response.send_message("❌ 无效金额", ephemeral=True)

        user_money = await get_user_money(self.user_id)
        current_loan = await get_loan_amount(self.user_id)

        if self.action == "借款":
            max_loan = 50000.00
            if current_loan + amount > max_loan:
                return await interaction.response.send_message(
                    f"🚫 额度超限！当前欠款 **{current_loan:.2f}**，最大额度 **{max_loan:.2f}**。",
                    ephemeral=True,
                )
            await borrow_money(self.user_id, amount)
            message = f"🤝 借款成功！获得 **{amount:.2f}** 喵币。"
        else:
            if user_money < amount:
                return await interaction.response.send_message(
                    f"🚫 现金不足！你有 **{user_money:.2f}**。",
                    ephemeral=True,
                )

            real_repay = round(min(amount, current_loan), 2)
            if real_repay <= 0:
                return await interaction.response.send_message("你没有欠款！", ephemeral=True)

            await repay_loan(self.user_id, real_repay)
            message = f"✅ 还款成功！偿还了 **{real_repay:.2f}** 喵币。"

        await interaction.response.send_message(message, ephemeral=True)


class StockDashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="买入", style=discord.ButtonStyle.success, emoji="📈", row=0)
    async def buy_btn(self, button, interaction):
        await interaction.response.send_message(
            "请选择要买入的股票：",
            view=TradeView("buy", interaction.user.id),
            ephemeral=True,
        )

    @discord.ui.button(label="卖出", style=discord.ButtonStyle.danger, emoji="📉", row=0)
    async def sell_btn(self, button, interaction):
        await interaction.response.send_message(
            "请选择要卖出的股票：",
            view=TradeView("sell", interaction.user.id),
            ephemeral=True,
        )

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def refresh_btn(self, button, interaction):
        await interaction.response.defer()
        embed = await render_market_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="资产", style=discord.ButtonStyle.primary, emoji="💼", row=1)
    async def portfolio_btn(self, button, interaction):
        user_id = interaction.user.id
        cash = await get_user_money(user_id)
        loan = await get_loan_amount(user_id)
        positions = await get_portfolio_with_prices(user_id)
        total_assets, content = summarize_portfolio(cash, loan, positions)

        embed = discord.Embed(title="💼 资产组合", description=content, color=0xF1C40F)
        embed.set_footer(text=f"净资产估值: {total_assets:.2f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="融资", style=discord.ButtonStyle.secondary, emoji="🏦", row=1)
    async def loan_btn(self, button, interaction):
        view = View()
        view.add_item(Button(label="借款", style=discord.ButtonStyle.success, custom_id="borrow"))
        view.add_item(Button(label="还款", style=discord.ButtonStyle.danger, custom_id="repay"))

        async def callback(inner_interaction):
            action = "借款" if inner_interaction.custom_id == "borrow" else "还款"
            await inner_interaction.response.send_modal(LoanModal(inner_interaction.user.id, action))

        view.children[0].callback = callback
        view.children[1].callback = callback
        await interaction.response.send_message("选择业务：", view=view, ephemeral=True)

    @discord.ui.button(label="指南", style=discord.ButtonStyle.secondary, emoji="📖", row=1)
    async def guide_btn(self, button, interaction):
        await interaction.response.send_message(embed=get_guide_embed(), ephemeral=True)


class StockMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.runtime_ready = False
        self.compensation_view = CompensationClaimView()
        self.panel_lock = asyncio.Lock()

    def cog_unload(self):
        if self.market_update.is_running():
            self.market_update.cancel()

    async def ensure_runtime_ready(self):
        if self.runtime_ready:
            return
        self.bot.add_view(self.compensation_view)
        if not self.market_update.is_running():
            self.market_update.start()
        self.runtime_ready = True

    async def initialize_stocks(self):
        if not os.path.exists("./data"):
            os.makedirs("./data")
        await initialize_stocks(STOCKS)

    @tasks.loop(minutes=20)
    async def market_update(self):
        await self.publish_market_update()

    async def publish_market_update(self):
        channel = None
        try:
            news_embed, now_str = await build_stock_news_embed()
            channel = self.bot.get_channel(NEWS_CHANNEL_ID)
            if not channel:
                return
            await self.ensure_news_panel_stack_bottom(channel=channel, embed=news_embed)
            print(f"[{now_str}] 股市新闻已更新")
        except Exception as exc:
            print(f"[StockMarket] market update failed: {exc}")
            if channel is not None:
                news_embed = discord.Embed(
                    title=STOCK_NEWS_TITLE,
                    color=0x3498DB,
                    url=f"https://panel.local/{STOCK_NEWS_PANEL_ID}",
                )
                news_embed.description = "股市面板刷新时出现异常，请等待下一轮自动更新。"
                news_embed.set_footer(text=f"面板ID:{STOCK_NEWS_PANEL_ID}")
                await self.ensure_news_panel_stack_bottom(channel=channel, embed=news_embed)

    @market_update.before_loop
    async def before_market_update(self):
        await self.bot.wait_until_ready()
        db_ready_event = getattr(self.bot, "db_ready_event", None)
        if db_ready_event is not None:
            await db_ready_event.wait()
        await asyncio.sleep(3)
        try:
            await self.initialize_stocks()
            await self.publish_market_update()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        db_ready_event = getattr(self.bot, "db_ready_event", None)
        if db_ready_event is not None:
            await db_ready_event.wait()
        await self.ensure_runtime_ready()

    async def find_stock_panel_messages(self, channel):
        panel_messages = []
        async for message in channel.history(limit=100):
            if is_stock_news_message(message):
                panel_messages.append(message)
        return panel_messages

    async def ensure_news_panel_stack_bottom(self, channel=None, embed=None):
        async with self.panel_lock:
            channel = channel or self.bot.get_channel(NEWS_CHANNEL_ID)
            if channel is None:
                return

            panel_messages = await self.find_stock_panel_messages(channel)
            newest_panel = panel_messages[0] if panel_messages else None

            signin_cog = self.bot.get_cog("DailySignin")
            signin_panel = None
            if signin_cog is not None:
                signin_panel = await signin_cog.get_latest_panel_message(channel)

            should_update_existing = embed is not None
            if embed is None:
                if newest_panel is not None and newest_panel.embeds:
                    embed = newest_panel.embeds[0]
                else:
                    embed, _ = await build_stock_news_embed()

            if newest_panel is not None and should_update_existing:
                try:
                    await newest_panel.edit(embed=embed)
                except discord.NotFound:
                    newest_panel = None

            ordered_panel = newest_panel
            should_recreate = (
                ordered_panel is None
                or signin_panel is None
                or ordered_panel.id > signin_panel.id
            )

            if should_recreate:
                ordered_panel = await channel.send(embed=embed)

            for message in panel_messages:
                if ordered_panel is not None and message.id != ordered_panel.id:
                    try:
                        await message.delete()
                    except Exception:
                        pass

            return ordered_panel

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id != NEWS_CHANNEL_ID:
            return
        await self.ensure_news_panel_stack_bottom(channel=message.channel)

    async def backfill_registered_role(self, guild: discord.Guild):
        role = guild.get_role(REGISTERED_ROLE_ID)
        if role is None:
            return {"granted": 0, "skipped_existing": 0, "skipped_missing": 0, "failed": 0, "role_missing": True}

        registered_user_ids = await list_registered_user_ids()
        granted = 0
        skipped_existing = 0
        skipped_missing = 0
        failed = 0

        for index, user_id in enumerate(registered_user_ids, start=1):
            member = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    skipped_missing += 1
                    await asyncio.sleep(1.2)
                    continue
                except discord.HTTPException:
                    failed += 1
                    await asyncio.sleep(2)
                    continue

            if role in member.roles:
                skipped_existing += 1
            else:
                try:
                    await member.add_roles(role, reason="已注册喵喵补发身份组")
                    granted += 1
                except discord.HTTPException:
                    failed += 1

            await asyncio.sleep(1.2)
            if index % 20 == 0:
                await asyncio.sleep(3)

        return {
            "granted": granted,
            "skipped_existing": skipped_existing,
            "skipped_missing": skipped_missing,
            "failed": failed,
            "role_missing": False,
        }

    async def reset_market_data(self):
        await reset_stock_market(STOCKS)

    async def check_bankruptcy(self, ctx, user_id):
        pass


def setup(bot):
    bot.add_cog(StockMarket(bot))
