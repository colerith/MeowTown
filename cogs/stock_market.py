# cogs/stock_market.py
import discord
import random
import aiosqlite
import asyncio
import datetime
from discord.ext import commands, tasks
from discord.ui import View, Select, Button, Modal, InputText
from utils.db import get_citizen, update_money, set_user_status
from utils.stock_data import STOCKS, generate_dynamic_news

DB_PATH = "./data/meowtown.db"
NEWS_CHANNEL_ID = # cogs/stock_market.py
import discord
import random
import aiosqlite
import asyncio
import datetime
from discord.ext import commands, tasks
from discord.ui import View, Select, Button, Modal, InputText
from utils.db import get_citizen, update_money, set_user_status
from utils.stock_data import STOCKS, generate_dynamic_news

DB_PATH = "./data/meowtown.db"
NEWS_CHANNEL_ID = 1443488941045977140 # 请确保这里填对你的频道ID
MAX_LOAN_RATIO = 2.0
IMG_STOCK = "https://i.postimg.cc/gcSBzV0j/stock-market.png"
IMG_UNLUCKY = "https://i.postimg.cc/QN4n8QMH/unlucky.png"

# --- 辅助函数：生成指南 Embed ---
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
        inline=False
    )
    
    embed.add_field(
        name="🎮 核心玩法",
        value=(
            "**1. 市场刷新**: 每 **20分钟** 刷新一次价格和新闻。\n"
            "**2. 看新闻**: 新闻是价格的风向标！利好买入，利空卖出。\n"
            "**3. 操作**: 点击按钮即可买入/卖出，无需指令。"
        ),
        inline=False
    )
    
    embed.add_field(
        name="☠️ 杠杆与破产",
        value=(
            "**🏦 融资**: 可向黑帮借贷最高 **200%** 净资产的钱。\n"
            "**🚨 破产**: 如果亏损导致 **净资产为负**，将触发强制平仓，现金归零，且**农场被抵押**！"
        ),
        inline=False
    )
    
    embed.set_footer(text="投资有风险，入市需谨慎 | 祝各位喵老板发大财！")
    return embed

async def render_market_embed():
    embed = discord.Embed(title="📊 喵尔街实时行情", color=0x1abc9c)
    embed.set_image(url=IMG_STOCK)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT stock_id, current_price, last_change FROM stocks ORDER BY stock_id") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                embed.description = "市场尚未开盘..."
                return embed
            for row in rows:
                stock_id, price, change = row
                data = STOCKS.get(stock_id, {"icon": "❓", "name": "未知"})
                
                if change > 0:
                    trend = f"🔼 +{change:.2f}"
                elif change < 0:
                    trend = f"🔽 {change:.2f}"
                else:
                    trend = "⏺️ 0.00"

                # 防止除以零错误
                pct = (change / (price - change)) * 100 if (price - change) != 0 else 0
                
                embed.add_field(
                    name=f"{data['icon']} {data['name']} ({stock_id})",
                    value=f"Price: **{price:.2f}**\nTrend: {trend} ({pct:+.1f}%)",
                    inline=True
                )
    embed.set_footer(text="数据每20分钟刷新一次 | 投资有风险，入市需谨慎")
    return embed

# --- 交易弹窗 ---
class TradeModal(Modal):
    def __init__(self, stock_id, action, current_price, user_id):
        super().__init__(title=f"{action} {stock_id}")
        self.stock_id = stock_id
        self.action = action
        self.price = current_price
        self.user_id = user_id
        self.add_item(InputText(label="数量", placeholder="请输入整数 (例如: 100)"))

    async def callback(self, interaction: discord.Interaction):
        # 1. 验证输入数量
        try:
            val_str = self.children[0].value
            if not val_str.isdigit():
                return await interaction.response.send_message("❌ 请输入纯数字！", ephemeral=True)
            amount = int(val_str)
            if amount <= 0: raise ValueError
        except:
            return await interaction.response.send_message("❌ 请输入有效的正整数！", ephemeral=True)

        # 2. 计算总价 (保留2位小数)
        total_val = round(self.price * amount, 2)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # 获取用户当前余额
            async with db.execute("SELECT money FROM users WHERE user_id = ?", (self.user_id,)) as cursor:
                row = await cursor.fetchone()
                user_money = row[0] if row else 0.0

            if self.action == "买入":
                if user_money < total_val:
                    return await interaction.response.send_message(f"🚫 余额不足！需要 {total_val:.2f}，你有 {user_money:.2f}。", ephemeral=True)
                
                await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_val, self.user_id))
                
                # UPSERT 持仓
                await db.execute("""
                    INSERT INTO portfolios (user_id, stock_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, stock_id) DO UPDATE SET quantity = quantity + excluded.quantity
                """, (self.user_id, self.stock_id, amount))
                msg = f"✅ 以 **{self.price:.2f}** 买入 **{amount}** 股 **{self.stock_id}**，花费 **{total_val:.2f}** 喵币。"

            elif self.action == "卖出":
                # 查询持仓
                cursor = await db.execute("SELECT quantity FROM portfolios WHERE user_id = ? AND stock_id = ?", (self.user_id, self.stock_id))
                row = await cursor.fetchone()
                
                if not row or row[0] < amount:
                    return await interaction.response.send_message("🚫 持仓不足！无法卖出。", ephemeral=True)
                
                new_qty = row[0] - amount
                if new_qty == 0:
                    await db.execute("DELETE FROM portfolios WHERE user_id = ? AND stock_id = ?", (self.user_id, self.stock_id))
                else:
                    await db.execute("UPDATE portfolios SET quantity = ? WHERE user_id = ? AND stock_id = ?", (new_qty, self.user_id, self.stock_id))
                
                # 直接执行加钱
                await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (total_val, self.user_id))
                msg = f"✅ 以 **{self.price:.2f}** 卖出 **{amount}** 股 **{self.stock_id}**，获得 **{total_val:.2f}** 喵币。"
            
            await db.commit()
        
        await interaction.response.send_message(msg, ephemeral=True)

# --- 股票选择菜单 ---
class StockSelect(Select):
    def __init__(self, action, user_id):
        self.action_type = action 
        self.user_id = user_id
        options = []
        for sid, data in STOCKS.items():
            options.append(discord.SelectOption(label=f"{sid} - {data['name']}", value=sid, emoji=data['icon']))
        super().__init__(placeholder=f"选择要{action}的股票...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        stock_id = self.values[0]
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (stock_id,))
            row = await cursor.fetchone()
            current_price = row[0] if row else 0
            
        action_name = "买入" if self.action_type == "buy" else "卖出"
        await interaction.response.send_modal(TradeModal(stock_id, action_name, current_price, self.user_id))

class TradeView(View):
    def __init__(self, action, user_id):
        super().__init__(timeout=60)
        self.add_item(StockSelect(action, user_id))

# --- 融资/还款 ---
class LoanModal(Modal):
    def __init__(self, user_id, action):
        super().__init__(title=f"{action}中心")
        self.user_id = user_id
        self.action = action
        self.add_item(InputText(label="金额", placeholder="请输入数字 (可带小数)"))

    async def callback(self, interaction: discord.Interaction):
        try:
            val_str = self.children[0].value
            # 【修改点】支持 float 输入
            amount = float(val_str)
            # 【修改点】强制保留2位小数
            amount = round(amount, 2)
            if amount <= 0: raise ValueError
        except:
            return await interaction.response.send_message("❌ 无效金额", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            # 获取用户余额
            async with db.execute("SELECT money FROM users WHERE user_id = ?", (self.user_id,)) as cursor:
                res = await cursor.fetchone()
                user_money = res[0] if res else 0.0

            if self.action == "借款":
                max_loan = 50000.00
                cursor = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (self.user_id,))
                row = await cursor.fetchone()
                curr_loan = row[0] if row else 0.0
                
                if curr_loan + amount > max_loan:
                    # 【修改点】格式化显示
                    return await interaction.response.send_message(f"🚫 额度超限！当前欠款 **{curr_loan:.2f}**，最大额度 **{max_loan:.2f}**。", ephemeral=True)
                
                await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, self.user_id))
                await db.execute("""
                    INSERT INTO loans (user_id, loan_amount) VALUES (?, ?) 
                    ON CONFLICT(user_id) DO UPDATE SET loan_amount = loan_amount + excluded.loan_amount
                """, (self.user_id, amount))
                # 【修改点】格式化显示
                msg = f"🤝 借款成功！获得 **{amount:.2f}** 喵币。"

            else: # 还款
                if user_money < amount: 
                    # 【修改点】格式化显示
                    return await interaction.response.send_message(f"🚫 现金不足！你有 **{user_money:.2f}**。", ephemeral=True)
                
                cursor = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (self.user_id,))
                row = await cursor.fetchone()
                curr_loan = row[0] if row else 0.0
                
                real_repay = min(amount, curr_loan)
                real_repay = round(real_repay, 2)
                
                if real_repay <= 0: 
                    return await interaction.response.send_message("你没有欠款！", ephemeral=True)
                
                await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (real_repay, self.user_id))
                await db.execute("UPDATE loans SET loan_amount = loan_amount - ? WHERE user_id = ?", (real_repay, self.user_id))
                # 【修改点】格式化显示
                msg = f"✅ 还款成功！偿还了 **{real_repay:.2f}** 喵币。"
            
            await db.commit()
        await interaction.response.send_message(msg, ephemeral=True)

# --- 主控面板 ---
class StockDashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="买入", style=discord.ButtonStyle.success, emoji="📈", row=0)
    async def buy_btn(self, button, interaction):
        await interaction.response.send_message("请选择要买入的股票：", view=TradeView("buy", interaction.user.id), ephemeral=True)

    @discord.ui.button(label="卖出", style=discord.ButtonStyle.danger, emoji="📉", row=0)
    async def sell_btn(self, button, interaction):
        await interaction.response.send_message("请选择要卖出的股票：", view=TradeView("sell", interaction.user.id), ephemeral=True)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def refresh_btn(self, button, interaction):
        await interaction.response.defer() 
        embed = await render_market_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="资产", style=discord.ButtonStyle.primary, emoji="💼", row=1)
    async def portfolio_btn(self, button, interaction):
        user_id = interaction.user.id
        async with aiosqlite.connect(DB_PATH) as db:
            user = await get_citizen(user_id)
            cash = user[4]
            cursor = await db.execute("SELECT stock_id, quantity FROM portfolios WHERE user_id = ?", (user_id,))
            rows = await cursor.fetchall()
            l_cur = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (user_id,))
            loan = (await l_cur.fetchone() or [0])[0]

        total_assets = cash - loan
        content = f"💰 现金: {cash:.2f}\n💸 贷款: {loan:.2f}\n\n**持仓:**\n"
        if not rows: content += "无"
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                for sid, qty in rows:
                    p_row = await (await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (sid,))).fetchone()
                    price = p_row[0] if p_row else 0
                    val = price * qty
                    total_assets += val
                    content += f"{sid}: {qty}股 (≈{val:.2f})\n"
        
        embed = discord.Embed(title="💼 资产组合", description=content, color=0xf1c40f)
        embed.set_footer(text=f"净资产估值: {total_assets:.2f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="融资", style=discord.ButtonStyle.secondary, emoji="🏦", row=1)
    async def loan_btn(self, button, interaction):
        view = View()
        view.add_item(Button(label="借款", style=discord.ButtonStyle.success, custom_id="borrow"))
        view.add_item(Button(label="还款", style=discord.ButtonStyle.danger, custom_id="repay"))
        
        async def callback(i):
            action = "借款" if i.custom_id == "borrow" else "还款"
            await i.response.send_modal(LoanModal(i.user.id, action))
            
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
        import os
        if not os.path.exists("./data"): os.makedirs("./data")
        async with aiosqlite.connect(DB_PATH) as db:
            for stock_id, data in STOCKS.items():
                cursor = await db.execute("SELECT 1 FROM stocks WHERE stock_id = ?", (stock_id,))
                if not await cursor.fetchone():
                    await db.execute("INSERT INTO stocks (stock_id, current_price) VALUES (?, ?)", (stock_id, data['base_price']))
            await db.commit()

    @tasks.loop(minutes=20)
    async def market_update(self):
        news_embed = discord.Embed(title="📈 喵尔街快讯", color=0x3498db)
        
        async with aiosqlite.connect(DB_PATH) as db:
            for stock_id, data in STOCKS.items():
                news, score = generate_dynamic_news(stock_id)
                cursor = await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (stock_id,))
                row = await cursor.fetchone()
                current_price = row[0] if row else data['base_price']
                
                change_percent = (score * 0.05) + random.uniform(-data["volatility"]/2, data["volatility"]/2)
                new_price = max(1, current_price * (1 + change_percent))
                
                await db.execute("UPDATE stocks SET current_price = ?, last_change = ? WHERE stock_id = ?", (new_price, new_price - current_price, stock_id))
                
                diff = new_price - current_price
                icon = "🔼" if diff > 0 else "🔽"
                pct = (diff / current_price) * 100 if current_price != 0 else 0
                
                news_embed.add_field(
                    name=f"{data['icon']} {data['name']}", 
                    value=f"**{new_price:.2f}** {icon} ({pct:+.2f}%)\n> {news}", 
                    inline=False
                )
            await db.commit()
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        news_embed.set_footer(text=f"最后刷新: {now_str} | 20分钟更新一次")

        channel = self.bot.get_channel(NEWS_CHANNEL_ID)
        if channel:
            bot_messages = []
            async for message in channel.history(limit=20):
                if message.author == self.bot.user:
                    bot_messages.append(message)
            
            if bot_messages:
                latest_msg = bot_messages[0]
                try:
                    await latest_msg.edit(embed=news_embed)
                    print(f"[{now_str}] 股市新闻已更新 (Edit)")
                    if len(bot_messages) > 1:
                        for old_msg in bot_messages[1:]:
                            await old_msg.delete()
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
        try: await self.initialize_stocks()
        except: pass

    @stock.command(name="大厅", description="打开股票交易终端")
    async def stock_dashboard(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        embed = await render_market_embed()
        await ctx.respond(embed=embed, view=StockDashboardView())

    async def check_bankruptcy(self, ctx, user_id):
        pass

def setup(bot):
    bot.add_cog(StockMarket(bot))
 # 请确保这里填对你的频道ID
MAX_LOAN_RATIO = 2.0
IMG_STOCK = "https://i.postimg.cc/gcSBzV0j/stock-market.png"
IMG_UNLUCKY = "https://i.postimg.cc/QN4n8QMH/unlucky.png"

# --- 辅助函数：生成指南 Embed ---
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
        inline=False
    )
    
    embed.add_field(
        name="🎮 核心玩法",
        value=(
            "**1. 市场刷新**: 每 **20分钟** 刷新一次价格和新闻。\n"
            "**2. 看新闻**: 新闻是价格的风向标！利好买入，利空卖出。\n"
            "**3. 操作**: 点击按钮即可买入/卖出，无需指令。"
        ),
        inline=False
    )
    
    embed.add_field(
        name="☠️ 杠杆与破产",
        value=(
            "**🏦 融资**: 可向黑帮借贷最高 **200%** 净资产的钱。\n"
            "**🚨 破产**: 如果亏损导致 **净资产为负**，将触发强制平仓，现金归零，且**农场被抵押**！"
        ),
        inline=False
    )
    
    embed.set_footer(text="投资有风险，入市需谨慎 | 祝各位喵老板发大财！")
    return embed

async def render_market_embed():
    embed = discord.Embed(title="📊 喵尔街实时行情", color=0x1abc9c)
    embed.set_image(url=IMG_STOCK)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT stock_id, current_price, last_change FROM stocks ORDER BY stock_id") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                embed.description = "市场尚未开盘..."
                return embed
            for row in rows:
                stock_id, price, change = row
                data = STOCKS.get(stock_id, {"icon": "❓", "name": "未知"})
                
                if change > 0:
                    trend = f"🔼 +{change:.2f}"
                elif change < 0:
                    trend = f"🔽 {change:.2f}"
                else:
                    trend = "⏺️ 0.00"

                # 防止除以零错误
                pct = (change / (price - change)) * 100 if (price - change) != 0 else 0
                
                embed.add_field(
                    name=f"{data['icon']} {data['name']} ({stock_id})",
                    value=f"Price: **{price:.2f}**\nTrend: {trend} ({pct:+.1f}%)",
                    inline=True
                )
    embed.set_footer(text="数据每20分钟刷新一次 | 投资有风险，入市需谨慎")
    return embed

# --- 交易弹窗 ---
class TradeModal(Modal):
    def __init__(self, stock_id, action, current_price, user_id):
        super().__init__(title=f"{action} {stock_id}")
        self.stock_id = stock_id
        self.action = action
        self.price = current_price
        self.user_id = user_id
        self.add_item(InputText(label="数量", placeholder="请输入整数 (例如: 100)"))

    async def callback(self, interaction: discord.Interaction):
        # 1. 验证输入数量
        try:
            val_str = self.children[0].value
            if not val_str.isdigit():
                return await interaction.response.send_message("❌ 请输入纯数字！", ephemeral=True)
            amount = int(val_str)
            if amount <= 0: raise ValueError
        except:
            return await interaction.response.send_message("❌ 请输入有效的正整数！", ephemeral=True)

        # 2. 计算总价 (保留2位小数)
        total_val = round(self.price * amount, 2)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # 获取用户当前余额
            async with db.execute("SELECT money FROM users WHERE user_id = ?", (self.user_id,)) as cursor:
                row = await cursor.fetchone()
                user_money = row[0] if row else 0.0

            if self.action == "买入":
                if user_money < total_val:
                    return await interaction.response.send_message(f"🚫 余额不足！需要 {total_val:.2f}，你有 {user_money:.2f}。", ephemeral=True)
                
                await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (total_val, self.user_id))
                
                # UPSERT 持仓
                await db.execute("""
                    INSERT INTO portfolios (user_id, stock_id, quantity) VALUES (?, ?, ?)
                    ON CONFLICT(user_id, stock_id) DO UPDATE SET quantity = quantity + excluded.quantity
                """, (self.user_id, self.stock_id, amount))
                msg = f"✅ 以 **{self.price:.2f}** 买入 **{amount}** 股 **{self.stock_id}**，花费 **{total_val:.2f}** 喵币。"

            elif self.action == "卖出":
                # 查询持仓
                cursor = await db.execute("SELECT quantity FROM portfolios WHERE user_id = ? AND stock_id = ?", (self.user_id, self.stock_id))
                row = await cursor.fetchone()
                
                if not row or row[0] < amount:
                    return await interaction.response.send_message("🚫 持仓不足！无法卖出。", ephemeral=True)
                
                new_qty = row[0] - amount
                if new_qty == 0:
                    await db.execute("DELETE FROM portfolios WHERE user_id = ? AND stock_id = ?", (self.user_id, self.stock_id))
                else:
                    await db.execute("UPDATE portfolios SET quantity = ? WHERE user_id = ? AND stock_id = ?", (new_qty, self.user_id, self.stock_id))
                
                # 直接执行加钱
                await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (total_val, self.user_id))
                msg = f"✅ 以 **{self.price:.2f}** 卖出 **{amount}** 股 **{self.stock_id}**，获得 **{total_val:.2f}** 喵币。"
            
            await db.commit()
        
        await interaction.response.send_message(msg, ephemeral=True)

# --- 股票选择菜单 ---
class StockSelect(Select):
    def __init__(self, action, user_id):
        self.action_type = action 
        self.user_id = user_id
        options = []
        for sid, data in STOCKS.items():
            options.append(discord.SelectOption(label=f"{sid} - {data['name']}", value=sid, emoji=data['icon']))
        super().__init__(placeholder=f"选择要{action}的股票...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        stock_id = self.values[0]
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (stock_id,))
            row = await cursor.fetchone()
            current_price = row[0] if row else 0
            
        action_name = "买入" if self.action_type == "buy" else "卖出"
        await interaction.response.send_modal(TradeModal(stock_id, action_name, current_price, self.user_id))

class TradeView(View):
    def __init__(self, action, user_id):
        super().__init__(timeout=60)
        self.add_item(StockSelect(action, user_id))

# --- 融资/还款 ---
class LoanModal(Modal):
    def __init__(self, user_id, action):
        super().__init__(title=f"{action}中心")
        self.user_id = user_id
        self.action = action
        self.add_item(InputText(label="金额", placeholder="请输入数字 (可带小数)"))

    async def callback(self, interaction: discord.Interaction):
        try:
            val_str = self.children[0].value
            # 【修改点】支持 float 输入
            amount = float(val_str)
            # 【修改点】强制保留2位小数
            amount = round(amount, 2)
            if amount <= 0: raise ValueError
        except:
            return await interaction.response.send_message("❌ 无效金额", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            # 获取用户余额
            async with db.execute("SELECT money FROM users WHERE user_id = ?", (self.user_id,)) as cursor:
                res = await cursor.fetchone()
                user_money = res[0] if res else 0.0

            if self.action == "借款":
                max_loan = 50000.00
                cursor = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (self.user_id,))
                row = await cursor.fetchone()
                curr_loan = row[0] if row else 0.0
                
                if curr_loan + amount > max_loan:
                    # 【修改点】格式化显示
                    return await interaction.response.send_message(f"🚫 额度超限！当前欠款 **{curr_loan:.2f}**，最大额度 **{max_loan:.2f}**。", ephemeral=True)
                
                await db.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, self.user_id))
                await db.execute("""
                    INSERT INTO loans (user_id, loan_amount) VALUES (?, ?) 
                    ON CONFLICT(user_id) DO UPDATE SET loan_amount = loan_amount + excluded.loan_amount
                """, (self.user_id, amount))
                # 【修改点】格式化显示
                msg = f"🤝 借款成功！获得 **{amount:.2f}** 喵币。"

            else: # 还款
                if user_money < amount: 
                    # 【修改点】格式化显示
                    return await interaction.response.send_message(f"🚫 现金不足！你有 **{user_money:.2f}**。", ephemeral=True)
                
                cursor = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (self.user_id,))
                row = await cursor.fetchone()
                curr_loan = row[0] if row else 0.0
                
                real_repay = min(amount, curr_loan)
                real_repay = round(real_repay, 2)
                
                if real_repay <= 0: 
                    return await interaction.response.send_message("你没有欠款！", ephemeral=True)
                
                await db.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (real_repay, self.user_id))
                await db.execute("UPDATE loans SET loan_amount = loan_amount - ? WHERE user_id = ?", (real_repay, self.user_id))
                # 【修改点】格式化显示
                msg = f"✅ 还款成功！偿还了 **{real_repay:.2f}** 喵币。"
            
            await db.commit()
        await interaction.response.send_message(msg, ephemeral=True)

# --- 主控面板 ---
class StockDashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="买入", style=discord.ButtonStyle.success, emoji="📈", row=0)
    async def buy_btn(self, button, interaction):
        await interaction.response.send_message("请选择要买入的股票：", view=TradeView("buy", interaction.user.id), ephemeral=True)

    @discord.ui.button(label="卖出", style=discord.ButtonStyle.danger, emoji="📉", row=0)
    async def sell_btn(self, button, interaction):
        await interaction.response.send_message("请选择要卖出的股票：", view=TradeView("sell", interaction.user.id), ephemeral=True)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def refresh_btn(self, button, interaction):
        await interaction.response.defer() 
        embed = await render_market_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="资产", style=discord.ButtonStyle.primary, emoji="💼", row=1)
    async def portfolio_btn(self, button, interaction):
        user_id = interaction.user.id
        async with aiosqlite.connect(DB_PATH) as db:
            user = await get_citizen(user_id)
            cash = user[4]
            cursor = await db.execute("SELECT stock_id, quantity FROM portfolios WHERE user_id = ?", (user_id,))
            rows = await cursor.fetchall()
            l_cur = await db.execute("SELECT loan_amount FROM loans WHERE user_id = ?", (user_id,))
            loan = (await l_cur.fetchone() or [0])[0]

        total_assets = cash - loan
        content = f"💰 现金: {cash:.2f}\n💸 贷款: {loan:.2f}\n\n**持仓:**\n"
        if not rows: content += "无"
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                for sid, qty in rows:
                    p_row = await (await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (sid,))).fetchone()
                    price = p_row[0] if p_row else 0
                    val = price * qty
                    total_assets += val
                    content += f"{sid}: {qty}股 (≈{val:.2f})\n"
        
        embed = discord.Embed(title="💼 资产组合", description=content, color=0xf1c40f)
        embed.set_footer(text=f"净资产估值: {total_assets:.2f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="融资", style=discord.ButtonStyle.secondary, emoji="🏦", row=1)
    async def loan_btn(self, button, interaction):
        view = View()
        view.add_item(Button(label="借款", style=discord.ButtonStyle.success, custom_id="borrow"))
        view.add_item(Button(label="还款", style=discord.ButtonStyle.danger, custom_id="repay"))
        
        async def callback(i):
            action = "借款" if i.custom_id == "borrow" else "还款"
            await i.response.send_modal(LoanModal(i.user.id, action))
            
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
        import os
        if not os.path.exists("./data"): os.makedirs("./data")
        async with aiosqlite.connect(DB_PATH) as db:
            for stock_id, data in STOCKS.items():
                cursor = await db.execute("SELECT 1 FROM stocks WHERE stock_id = ?", (stock_id,))
                if not await cursor.fetchone():
                    await db.execute("INSERT INTO stocks (stock_id, current_price) VALUES (?, ?)", (stock_id, data['base_price']))
            await db.commit()

    @tasks.loop(minutes=20)
    async def market_update(self):
        news_embed = discord.Embed(title="📈 喵尔街快讯", color=0x3498db)
        
        async with aiosqlite.connect(DB_PATH) as db:
            for stock_id, data in STOCKS.items():
                news, score = generate_dynamic_news(stock_id)
                cursor = await db.execute("SELECT current_price FROM stocks WHERE stock_id = ?", (stock_id,))
                row = await cursor.fetchone()
                current_price = row[0] if row else data['base_price']
                
                change_percent = (score * 0.05) + random.uniform(-data["volatility"]/2, data["volatility"]/2)
                new_price = max(1, current_price * (1 + change_percent))
                
                await db.execute("UPDATE stocks SET current_price = ?, last_change = ? WHERE stock_id = ?", (new_price, new_price - current_price, stock_id))
                
                diff = new_price - current_price
                icon = "🔼" if diff > 0 else "🔽"
                pct = (diff / current_price) * 100 if current_price != 0 else 0
                
                news_embed.add_field(
                    name=f"{data['icon']} {data['name']}", 
                    value=f"**{new_price:.2f}** {icon} ({pct:+.2f}%)\n> {news}", 
                    inline=False
                )
            await db.commit()
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        news_embed.set_footer(text=f"最后刷新: {now_str} | 20分钟更新一次")

        channel = self.bot.get_channel(NEWS_CHANNEL_ID)
        if channel:
            bot_messages = []
            async for message in channel.history(limit=20):
                if message.author == self.bot.user:
                    bot_messages.append(message)
            
            if bot_messages:
                latest_msg = bot_messages[0]
                try:
                    await latest_msg.edit(embed=news_embed)
                    print(f"[{now_str}] 股市新闻已更新 (Edit)")
                    if len(bot_messages) > 1:
                        for old_msg in bot_messages[1:]:
                            await old_msg.delete()
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
        try: await self.initialize_stocks()
        except: pass

    @stock.command(name="大厅", description="打开股票交易终端")
    async def stock_dashboard(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        embed = await render_market_embed()
        await ctx.respond(embed=embed, view=StockDashboardView())

    async def check_bankruptcy(self, ctx, user_id):
        pass

def setup(bot):
    bot.add_cog(StockMarket(bot))

