# cogs/farm.py
import discord
import time
import random
import asyncio
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
from utils.db import (
    get_citizen, update_money, get_farm_state, plant_seed, clear_plot, 
    add_farm_plot, get_items, use_item_from_db, add_item,
    get_all_active_farms, mark_farm_notified
)
from utils.farm_data import PLANTS, get_plant_by_name, calculate_harvest, RARITY
from utils.shop_data import SHOP_ITEMS

# 土地扩建价格表
LAND_PRICES = {
    4: 5000,    5: 15000,   6: 50000,   7: 150000,  8: 500000
}

# --- 辅助函数：生成农场状态 Embed ---
async def render_farm_embed(user_id, user_name, avatar_url):
    plots = await get_farm_state(user_id)
    current_time = int(time.time())
    plots.sort(key=lambda x: x[1])
    
    embed = discord.Embed(title=f"🏡 {user_name} 的喵喵农场", color=0x2ecc71)
    embed.set_image(url="https://i.postimg.cc/L4C09ts2/farm.png")
    
    status_text = ""
    ready_count = 0
    empty_count = 0
    
    for row in plots:
        plot_id = row[1]
        plant_id = row[2]
        planted_at = row[3]
        plot_num = plot_id + 1
        
        if plant_id is None:
            status_text += f"`[{plot_num}]` 🟫 **空闲**\n"
            empty_count += 1
        else:
            plant = PLANTS[plant_id]
            elapsed = current_time - planted_at
            required = plant["time"]
            
            if elapsed >= required:
                status_text += f"`[{plot_num}]` {plant['icon']} **{plant['name']}** (已成熟!)\n"
                ready_count += 1
            else:
                percent = min(100, int((elapsed / required) * 100))
                # 进度条
                bar_length = 6
                filled = int(percent / (100 / bar_length))
                bar = "🟩" * filled + "⬜" * (bar_length - filled)
                
                left_seconds = required - elapsed
                if left_seconds > 3600:
                    left_str = f"{left_seconds//3600}小时{(left_seconds%3600)//60}分"
                else:
                    left_str = f"{left_seconds//60}分{left_seconds%60}秒"
                
                status_text += f"`[{plot_num}]` {plant['icon']} {bar} {left_str}\n"
    
    embed.description = status_text
    
    # 底部状态栏
    footer_text = f"空地: {empty_count} | 可收获: {ready_count}"
    
    current_plot_count = len(plots)
    if current_plot_count < 9:
        next_price = LAND_PRICES.get(current_plot_count, 999999)
        footer_text += f" | 下块地: {next_price}喵币"
    else:
        footer_text += " | 土地已满"
        
    embed.set_footer(text=footer_text)
    return embed

# --- UI 组件：种子/道具选择菜单 ---

class FarmSelect(Select):
    """通用的选择菜单，支持植物和农资道具"""
    def __init__(self, category, parent_view):
        self.parent_view = parent_view
        self.category = category # "N", "R", ... or "tool"
        options = []
        
        if category == "tool":
            # 加载农场道具 (从 SHOP_ITEMS 中筛选 type='farm')
            for name, item in SHOP_ITEMS.items():
                if item['type'] == 'farm':
                    options.append(discord.SelectOption(
                        label=name,
                        value=name,
                        description=f"💰{item['price']} | {item['desc'][:30]}",
                        emoji=item['icon']
                    ))
            placeholder = "选择农资道具..."
        else:
            # 加载种子 (从 PLANTS 中筛选稀有度)
            sorted_plants = sorted(PLANTS.items(), key=lambda x: int(x[0]))
            for pid, data in sorted_plants:
                if data['rarity'] == category:
                    time_min = data['time'] // 60
                    time_str = f"{time_min}分" if time_min < 60 else f"{time_min//60}小时"
                    options.append(discord.SelectOption(
                        label=data['name'],
                        value=pid,
                        description=f"💰{data['cost']} | ⏳{time_str}",
                        emoji=data['icon']
                    ))
            placeholder = f"选择 {RARITY[category]['name']} 作物..."
        
        if not options:
            options.append(discord.SelectOption(label="该分类暂无商品", value="none"))

        super().__init__(
            placeholder=placeholder,
            min_values=1, max_values=1, options=options[:25], row=1
        )

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "none": return
        
        self.parent_view.selected_item = val
        # 如果当前分类是 tool，标记选中的是道具
        self.parent_view.is_tool = (self.category == "tool")
        await self.parent_view.update_embed(interaction)

class FarmShopView(View):
    """购买并种植/购买道具的二级界面"""
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_category = "N" # 默认普通
        self.selected_item = None
        self.is_tool = False
        self.setup_ui()

    def setup_ui(self):
        self.clear_items()
        
        # 1. 稀有度按钮 (Row 0)
        for r_key, r_data in RARITY.items():
            btn = Button(
                label=r_data['name'], 
                style=discord.ButtonStyle.primary if r_key == self.selected_category else discord.ButtonStyle.secondary, 
                custom_id=f"cat_{r_key}", 
                row=0
            )
            btn.callback = self.switch_category
            self.add_item(btn)
        
        # 2. 道具分类按钮 (Row 0)
        btn_tool = Button(
            label="农资道具", 
            style=discord.ButtonStyle.success if self.selected_category == "tool" else discord.ButtonStyle.secondary, 
            custom_id="cat_tool", 
            emoji="🧪", 
            row=0
        )
        btn_tool.callback = self.switch_category
        self.add_item(btn_tool)
        
        # 3. 下拉菜单 (Row 1)
        self.add_item(FarmSelect(self.selected_category, self))
        
        # 4. 操作按钮 (Row 2) - 动态变化
        if self.is_tool:
            # 如果选的是道具，显示购买按钮
            btn_buy = Button(label="购买", style=discord.ButtonStyle.success, emoji="🛒", row=2)
            btn_buy.callback = self.action_buy_tool
            self.add_item(btn_buy)
        else:
            # 如果选的是种子，显示种植按钮
            btn_plant_1 = Button(label="种植 x1", style=discord.ButtonStyle.success, emoji="🌱", row=2)
            btn_plant_1.callback = lambda i: self.action_plant(i, 1)
            self.add_item(btn_plant_1)
            
            btn_fill = Button(label="填满空地", style=discord.ButtonStyle.success, emoji="🚜", row=2)
            btn_fill.callback = lambda i: self.action_plant(i, 99)
            self.add_item(btn_fill)

    async def switch_category(self, interaction: discord.Interaction):
        # 获取按钮 custom_id 的后缀 (N, R, tool...)
        self.selected_category = interaction.custom_id.split("_")[1]
        self.selected_item = None
        self.is_tool = (self.selected_category == "tool")
        
        self.setup_ui() # 重建UI
        await self.update_embed(interaction)

    async def update_embed(self, interaction: discord.Interaction):
        if not self.selected_item:
            embed = discord.Embed(title="🏪 农场商店", description="请点击上方按钮切换分类，并在菜单中选择商品。", color=0x2ecc71)
        else:
            if self.is_tool:
                # 选了道具
                item = SHOP_ITEMS[self.selected_item]
                embed = discord.Embed(title=f"{item['icon']} {item['name']}", color=0xFF00FF)
                embed.add_field(name="💰 价格", value=f"**{item['price']}** 喵币", inline=True)
                embed.add_field(name="📝 效果", value=item['desc'], inline=False)
                embed.set_footer(text="点击【购买】放入背包")
            else:
                # 选了种子
                plant = PLANTS[self.selected_item]
                rarity_info = RARITY[plant['rarity']]
                embed = discord.Embed(title=f"{plant['icon']} {plant['name']}", color=rarity_info['color'])
                embed.add_field(name="💰 种子价格", value=f"**{plant['cost']}** 喵币", inline=True)
                
                t = plant['time']
                t_str = f"{t//3600}小时{(t%3600)//60}分" if t >= 3600 else f"{t//60}分"
                embed.add_field(name="⏳ 时间", value=t_str, inline=True)
                
                embed.add_field(name="⚖️ 预计产量", value=f"{plant['min']}~{plant['max']}", inline=True)
                embed.set_footer(text="点击【种植】直接购买并种下")
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def action_buy_tool(self, interaction: discord.Interaction):
        if not self.selected_item: return
        item_name = self.selected_item
        item = SHOP_ITEMS[item_name]
        user_id = interaction.user.id
        
        user = await get_citizen(user_id)
        if user[4] < item['price']:
            return await interaction.response.send_message("🚫 余额不足！", ephemeral=True)
            
        await update_money(user_id, -item['price'])
        await add_item(user_id, item_name, 1)
        
        await interaction.response.send_message(f"✅ 成功购买 **{item['name']}**！已放入背包。", ephemeral=True)

    async def action_plant(self, interaction: discord.Interaction, count):
        if not self.selected_item:
            return await interaction.response.send_message("❌ 请先选择作物！", ephemeral=True)
        
        user_id = interaction.user.id
        plant = PLANTS[self.selected_item]
        
        # 获取空地
        plots = await get_farm_state(user_id)
        empty_plots = [row[1] for row in plots if row[2] is None]
        
        if not empty_plots:
            return await interaction.response.send_message("🚫 没有空地了！", ephemeral=True)
            
        real_count = min(len(empty_plots), count)
        total_cost = real_count * plant['cost']
        
        user = await get_citizen(user_id)
        if user[4] < total_cost:
            # 钱不够时的逻辑：买得起多少买多少
            real_count = user[4] // plant['cost']
            total_cost = real_count * plant['cost']
            if real_count == 0:
                return await interaction.response.send_message("🚫 余额不足！", ephemeral=True)

        await update_money(user_id, -total_cost)
        now = int(time.time())
        
        for i in range(real_count):
            await plant_seed(user_id, empty_plots[i], self.selected_item, now)
            
        await interaction.response.send_message(f"✅ 成功种植了 {real_count} 棵 {plant['name']}，花费 {total_cost} 喵币。", ephemeral=True)

# --- UI 组件：主控面板 ---

class FarmDashboardView(View):
    def __init__(self, user_id, user_name, user_avatar):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.user_avatar = user_avatar

    async def refresh_farm(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的农场！", ephemeral=True)
        
        # 刷新操作因为是 update_message，通常不需要 defer，但为了稳妥可以 defer 
        # (不过 edit_message 本身响应很快，且是在已有交互上操作)
        embed = await render_farm_embed(self.user_id, self.user_name, self.user_avatar)
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except: 
            # 如果 response 已经用过了 (比如报错)，尝试 edit
            try: await interaction.message.edit(embed=embed, view=self)
            except: pass

    @discord.ui.button(label="农场商店", style=discord.ButtonStyle.primary, emoji="🏪", row=0)
    async def shop_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的农场！", ephemeral=True)
        view = FarmShopView(self.user_id)
        embed = discord.Embed(title="🏪 农场商店", description="购买种子或化肥。", color=0x2ecc71)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="收获", style=discord.ButtonStyle.success, emoji="🚜", row=0)
    async def harvest_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        # 收获逻辑可能会慢，Defer!
        await interaction.response.defer(ephemeral=True)
        
        plots = await get_farm_state(self.user_id)
        current_time = int(time.time())
        total_income = 0
        harvested = []
        
        for row in plots:
            if row[2]:
                plant = PLANTS[row[2]]
                if (current_time - row[3]) >= plant["time"]:
                    income = calculate_harvest(row[2])
                    total_income += income
                    harvested.append(plant['name'])
                    await clear_plot(self.user_id, row[1])
        
        if total_income > 0:
            await update_money(self.user_id, total_income)
            await interaction.followup.send(f"💰 收获了: {', '.join(harvested)}\n一共卖出 **{total_income}** 喵币！", ephemeral=True)
            # 刷新界面
            embed = await render_farm_embed(self.user_id, self.user_name, self.user_avatar)
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.followup.send("🚫 没有成熟的作物。", ephemeral=True)

    @discord.ui.button(label="背包", style=discord.ButtonStyle.secondary, emoji="🎒", row=1)
    async def bag_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        items = await get_items(self.user_id)
        farm_items = [i for i in items if i[0] in ["金坷垃", "超级金坷垃"]]
        
        if not farm_items:
            return await interaction.response.send_message("🎒 你的农资背包空空如也！请点击【农场商店】购买化肥。", ephemeral=True)
        
        msg = "**🎒 农资背包**\n"
        for name, count in farm_items:
            msg += f"🔹 **{name}** x{count}\n"
        
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="施肥", style=discord.ButtonStyle.secondary, emoji="🧪", row=1)
    async def fertilize_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        await interaction.response.defer(ephemeral=True)

        has_normal = await use_item_from_db(self.user_id, "金坷垃")
        if has_normal:
            reduce = 3600
            name = "金坷垃"
        else:
            has_super = await use_item_from_db(self.user_id, "超级金坷垃")
            if has_super:
                reduce = 18000
                name = "超级金坷垃"
            else:
                return await interaction.followup.send("🚫 你没有化肥！请点击【农场商店】购买。", ephemeral=True)
        
        import aiosqlite
        async with aiosqlite.connect("./data/meowtown.db") as db:
            await db.execute(
                "UPDATE farms SET planted_at = planted_at - ? WHERE user_id = ? AND plant_id IS NOT NULL",
                (reduce, self.user_id)
            )
            await db.commit()
            
        await interaction.followup.send(f"🧪 撒下了 **{name}**！所有作物加速生长了。", ephemeral=True)
        # 刷新界面
        embed = await render_farm_embed(self.user_id, self.user_name, self.user_avatar)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, button, interaction):
        await self.refresh_farm(interaction)

    @discord.ui.button(label="扩建", style=discord.ButtonStyle.danger, emoji="🏗️", row=1)
    async def expand_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        await interaction.response.defer(ephemeral=True)

        plots = await get_farm_state(self.user_id)
        current = len(plots)
        if current >= 9:
            return await interaction.followup.send("已达最大规模！", ephemeral=True)
            
        price = LAND_PRICES.get(current)
        user = await get_citizen(self.user_id)
        if user[4] < price:
            return await interaction.followup.send(f"资金不足！扩建需要 {price} 喵币。", ephemeral=True)
            
        await update_money(self.user_id, -price)
        await add_farm_plot(self.user_id, current)
        
        await interaction.followup.send(f"✅ 扩建成功！花费 {price} 喵币。", ephemeral=True)
        # 刷新界面
        embed = await render_farm_embed(self.user_id, self.user_name, self.user_avatar)
        await interaction.message.edit(embed=embed, view=self)

# --- Farm Cog ---

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.crop_checker.start()

    def cog_unload(self):
        self.crop_checker.cancel()

    farm = discord.SlashCommandGroup("农场", "经营你的喵喵农场")

    @farm.command(name="查看", description="打开农场控制面板")
    async def view(self, ctx: discord.ApplicationContext):
        # 【修复点】这里添加了 defer，防止初始加载超时
        await ctx.defer()
        embed = await render_farm_embed(ctx.author.id, ctx.author.display_name, ctx.author.display_avatar.url)
        view = FarmDashboardView(ctx.author.id, ctx.author.display_name, ctx.author.display_avatar.url)
        await ctx.respond(embed=embed, view=view)

    @farm.command(name="偷菜", description="潜入别人的农场偷菜")
    async def steal(self, ctx: discord.ApplicationContext, target: discord.User):
        if target.id == ctx.author.id:
            await ctx.respond("❓ 你不能偷自己的。", ephemeral=True)
            return

        # 【修复点】偷菜也添加了 defer
        await ctx.defer()

        plots = await get_farm_state(target.id)
        current_time = int(time.time())
        stealable = []
        
        for row in plots:
            if row[2]:
                plant = PLANTS[row[2]]
                if (current_time - row[3]) >= plant["time"]:
                    stealable.append(row)
        
        if not stealable:
            await ctx.respond("没熟或者没种，没法偷。", ephemeral=True)
            return

        target_plot = random.choice(stealable)
        plant_id = target_plot[2]
        plant = PLANTS[plant_id]
        
        if random.random() > 0.4:
            income = int(calculate_harvest(plant_id) * 0.8)
            await clear_plot(target.id, target_plot[1])
            await update_money(ctx.author.id, income)
            await ctx.respond(f"😈 偷到了 {target.mention} 的 **{plant['name']}**！卖了 {income} 喵币。")
        else:
            fine = 200
            await update_money(ctx.author.id, -fine)
            await ctx.respond(f"🐕 被 {target.mention} 的狗发现了！罚款 {fine} 喵币。")

    # --- 后台任务：检测作物并私信 ---
    @tasks.loop(minutes=2) 
    async def crop_checker(self):
        current_time = int(time.time())
        active_farms = await get_all_active_farms()
        notify_queue = {}
        
        for user_id, plant_id, planted_at in active_farms:
            plant = PLANTS[plant_id]
            if (current_time - planted_at) >= plant['time']:
                if user_id not in notify_queue: notify_queue[user_id] = []
                notify_queue[user_id].append(plant['name'])
                await mark_farm_notified(user_id, plant_id)

        for user_id, plant_names in notify_queue.items():
            try:
                user = await self.bot.fetch_user(user_id)
                if user:
                    unique_names = list(set(plant_names))
                    count_str = f"等 {len(plant_names)} 棵作物" if len(plant_names) > 1 else ""
                    
                    embed = discord.Embed(title="🚜 农场丰收提醒！", color=0x2ecc71)
                    embed.description = f"勤劳的喵喵，你的 **{', '.join(unique_names)}** {count_str}已经成熟了！\n快回小镇收菜吧！"
                    await user.send(embed=embed)
            except Exception as e:
                pass

    @crop_checker.before_loop
    async def before_checker(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Farm(bot))
