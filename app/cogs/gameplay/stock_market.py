import asyncio
import datetime
import os

import discord
from discord.ext import commands, tasks
from discord.ui import Button, InputText, Modal, Select, View

from app.db.repositories.stock_repo import (
    borrow_money,
    buy_stock,
    get_loan_amount,
    get_portfolio_with_prices,
    get_stock_price,
    initialize_stocks,
    list_market_stocks,
    repay_loan,
    sell_stock,
    update_stock_quote,
)
from app.db.repositories.user_repo import get_user_money
from app.features.stock_market.service import (
    format_market_trend,
    parse_positive_amount,
    parse_positive_int,
    summarize_portfolio,
)
from app.shared.data.stock_data import STOCKS, calculate_next_price, generate_dynamic_news

NEWS_CHANNEL_ID = 1443488941045977140
IMG_STOCK = "https://i.postimg.cc/gcSBzV0j/stock-market.png"
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
        self.market_update.start()

    def cog_unload(self):
        self.market_update.cancel()

    stock = discord.SlashCommandGroup("股市", "喵尔街股票交易中心")

    async def initialize_stocks(self):
        if not os.path.exists("./data"):
            os.makedirs("./data")
        await initialize_stocks(STOCKS)

    @tasks.loop(minutes=20)
    async def market_update(self):
        news_embed = discord.Embed(title="📈 喵尔街快讯", color=0x3498DB)

        for stock_id, data in STOCKS.items():
            current_price = await get_stock_price(stock_id) or data["base_price"]
            news, score = generate_dynamic_news(stock_id, current_price=current_price)
            new_price, change_pct = calculate_next_price(stock_id, current_price, score)
            price_diff = new_price - current_price
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
        news_embed.set_footer(text=f"最后刷新: {now_str} | 20分钟更新一次")

        channel = self.bot.get_channel(NEWS_CHANNEL_ID)
        if not channel:
            return

        bot_messages = []
        async for message in channel.history(limit=20):
            if message.author == self.bot.user:
                bot_messages.append(message)

        if bot_messages:
            latest_message = bot_messages[0]
            try:
                await latest_message.edit(embed=news_embed)
                print(f"[{now_str}] 股市新闻已更新 (Edit)")
                for old_message in bot_messages[1:]:
                    await old_message.delete()
                    await asyncio.sleep(1)
            except discord.NotFound:
                await channel.send(embed=news_embed)
        else:
            await channel.send(embed=news_embed)
            print(f"[{now_str}] 股市新闻已发送 (New)")

    @market_update.before_loop
    async def before_market_update(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)
        try:
            await self.initialize_stocks()
        except Exception:
            pass

    @stock.command(name="大厅", description="打开股票交易终端")
    async def stock_dashboard(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        embed = await render_market_embed()
        await ctx.respond(embed=embed, view=StockDashboardView())

    async def check_bankruptcy(self, ctx, user_id):
        pass


def setup(bot):
    bot.add_cog(StockMarket(bot))
