# cogs/farm.py
import discord
import time
import random
import asyncio
from discord.ext import commands, tasks
from discord.ui import View, Select, Button, InputText, Modal
from app.db.repositories.farm_repo import (
    accelerate_farm_growth,
    add_farm_plot,
    clear_plot,
    get_expired_farm_guards,
    get_all_active_farms,
    get_all_farming_users,
    get_farm_guard,
    get_farm_state,
    mark_farm_guard_notice_sent,
    mark_farm_notified,
    plant_seed,
    remove_farm_guard,
    set_farm_guard,
)
from app.db.repositories.inventory_repo import add_item, get_items, use_item_from_db
from app.db.repositories.user_repo import get_citizen, update_money
from app.shared.data.farm_data import (
    FARM_FERTILIZERS,
    FARM_GUARDS,
    PLANTS,
    RARITY,
    calculate_harvest,
    get_plant_by_name,
)
from app.shared.data.shop_data import SHOP_ITEMS

# 土地扩建价格表
LAND_PRICES = {
    4: 5000,    5: 15000,   6: 50000,   7: 150000,  8: 500000
}

# --- 辅助函数：生成农场状态 Embed ---
async def render_farm_embed(user_id, user_name, avatar_url):
    current_time = int(time.time())
    plots = await get_farm_state(user_id)
    plots.sort(key=lambda x: x[1])
    guard = await get_farm_guard(user_id, current_time=current_time)
    
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
    if guard:
        guard_type, expires_at = guard
        guard_info = FARM_GUARDS.get(guard_type)
        if guard_info:
            left_seconds = max(0, expires_at - current_time)
            left_hours = left_seconds // 3600
            left_minutes = (left_seconds % 3600) // 60
            embed.add_field(
                name="🛡️ 农场护卫",
                value=(
                    f"{guard_info['icon']} **{guard_info['name']}**\n"
                    f"拦截概率: **{int(guard_info['block_rate'] * 100)}%**\n"
                    f"剩余时间: **{left_hours}小时{left_minutes}分**"
                ),
                inline=False,
            )
    else:
        embed.add_field(name="🛡️ 农场护卫", value="当前未租赁护卫，容易被偷菜。", inline=False)
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
        await interaction.response.send_modal(FarmToolBuyModal(self.user_id, self.selected_item))

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


class FarmToolBuyModal(Modal):
    def __init__(self, user_id, item_name):
        super().__init__(title=f"购买 {item_name}")
        self.user_id = user_id
        self.item_name = item_name
        self.add_item(InputText(label="购买数量", value="1", placeholder="请输入 1-999 的整数"))

    async def callback(self, interaction: discord.Interaction):
        try:
            quantity = int(self.children[0].value)
        except ValueError:
            return await interaction.response.send_message("❌ 请输入 1-999 的整数。", ephemeral=True)

        if quantity < 1 or quantity > 999:
            return await interaction.response.send_message("❌ 单次购买数量必须在 1 到 999 之间。", ephemeral=True)

        item = SHOP_ITEMS[self.item_name]
        total_cost = item["price"] * quantity
        user = await get_citizen(self.user_id)
        if user[4] < total_cost:
            return await interaction.response.send_message(
                f"🚫 余额不足！购买 **{quantity}** 个需要 **{total_cost}** 喵币。",
                ephemeral=True,
            )

        await update_money(self.user_id, -total_cost)
        await add_item(self.user_id, self.item_name, quantity)
        await interaction.response.send_message(
            f"✅ 成功购买 **{self.item_name} x{quantity}**，花费 **{total_cost}** 喵币。",
            ephemeral=True,
        )


class GuardRentSelect(Select):
    def __init__(self, user_id, user_name, user_avatar):
        self.user_id = user_id
        self.user_name = user_name
        self.user_avatar = user_avatar
        options = [
            discord.SelectOption(
                label=guard["name"],
                value=guard_key,
                description=(
                    f"💰{guard['price']} | 拦截{int(guard['block_rate'] * 100)}% | "
                    f"{guard['duration_hours']}小时"
                ),
                emoji=guard["icon"],
            )
            for guard_key, guard in FARM_GUARDS.items()
        ]
        super().__init__(placeholder="选择要租赁的护卫...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guard_key = self.values[0]
        guard = FARM_GUARDS[guard_key]
        user = await get_citizen(self.user_id)
        if user[4] < guard["price"]:
            return await interaction.response.send_message(
                f"🚫 余额不足！租赁 **{guard['name']}** 需要 **{guard['price']}** 喵币。",
                ephemeral=True,
            )

        await update_money(self.user_id, -guard["price"])
        expires_at = int(time.time()) + guard["duration_hours"] * 3600
        await set_farm_guard(self.user_id, guard_key, expires_at)
        embed = await render_farm_embed(self.user_id, self.user_name, self.user_avatar)
        await interaction.response.send_message(
            f"🛡️ 已成功租赁 **{guard['icon']} {guard['name']}**，持续 **{guard['duration_hours']}** 小时。",
            ephemeral=True,
        )
        if interaction.message:
            await interaction.message.edit(embed=embed, view=FarmDashboardView(self.user_id, self.user_name, self.user_avatar))


class GuardRentView(View):
    def __init__(self, user_id, user_name, user_avatar):
        super().__init__(timeout=120)
        self.add_item(GuardRentSelect(user_id, user_name, user_avatar))


class StealTargetModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="指定用户偷菜")
        self.parent_view = parent_view
        self.add_item(InputText(label="目标用户 ID", placeholder="请输入对方的 Discord 用户 ID"))

    async def callback(self, interaction: discord.Interaction):
        raw = self.children[0].value.strip()
        if not raw.isdigit():
            return await interaction.response.send_message("❌ 请输入有效的用户 ID。", ephemeral=True)

        target_user_id = int(raw)
        if target_user_id == self.parent_view.user_id:
            return await interaction.response.send_message("❓ 你不能偷自己的菜。", ephemeral=True)

        result = await self.parent_view.execute_steal(interaction, target_user_id=target_user_id, random_target=False)
        await interaction.response.send_message(result, ephemeral=True)

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
        farm_items = [i for i in items if i[0] in FARM_FERTILIZERS]
        
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

        name = None
        reduce = None
        for item_name, data in sorted(FARM_FERTILIZERS.items(), key=lambda item: item[1]["seconds"], reverse=True):
            if await use_item_from_db(self.user_id, item_name):
                name = item_name
                reduce = data["seconds"]
                break

        if reduce is None:
            return await interaction.followup.send("🚫 你没有化肥！请点击【农场商店】购买。", ephemeral=True)
        
        await accelerate_farm_growth(self.user_id, reduce)
            
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

    @discord.ui.button(label="偷菜", style=discord.ButtonStyle.danger, emoji="😈", row=2)
    async def steal_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的农场！", ephemeral=True)

        view = View(timeout=120)
        random_btn = Button(label="随机偷菜", style=discord.ButtonStyle.danger, emoji="🎲")
        target_btn = Button(label="指定用户", style=discord.ButtonStyle.secondary, emoji="🎯")

        async def random_callback(inner_interaction):
            result = await self.execute_steal(inner_interaction, random_target=True)
            await inner_interaction.response.send_message(result, ephemeral=True)

        async def target_callback(inner_interaction):
            await inner_interaction.response.send_modal(StealTargetModal(self))

        random_btn.callback = random_callback
        target_btn.callback = target_callback
        view.add_item(random_btn)
        view.add_item(target_btn)
        await interaction.response.send_message("选择偷菜方式：", view=view, ephemeral=True)

    @discord.ui.button(label="租赁护卫", style=discord.ButtonStyle.primary, emoji="🛡️", row=2)
    async def guard_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的农场！", ephemeral=True)
        embed = discord.Embed(title="🛡️ 农场护卫租赁", description="选择一位护卫守住你的农场。", color=0x5865F2)
        await interaction.response.send_message(
            embed=embed,
            view=GuardRentView(self.user_id, self.user_name, self.user_avatar),
            ephemeral=True,
        )

    async def execute_steal(self, interaction: discord.Interaction, target_user_id=None, random_target=False):
        current_time = int(time.time())
        if random_target:
            candidate_ids = await get_all_farming_users(exclude_user_id=self.user_id)
            mature_candidates = []
            for user_id in candidate_ids:
                plots = await get_farm_state(user_id)
                has_mature = any(
                    row[2] and (current_time - row[3]) >= PLANTS[row[2]]["time"]
                    for row in plots
                )
                if has_mature:
                    mature_candidates.append(user_id)

            if not mature_candidates:
                return "🚫 当前没有可下手的成熟农场。"
            target_user_id = random.choice(mature_candidates)

        if target_user_id is None:
            return "🚫 未找到目标用户。"

        try:
            target = await interaction.client.fetch_user(target_user_id)
        except Exception:
            return "🚫 未找到目标用户。"
        plots = await get_farm_state(target_user_id)
        stealable = []
        for row in plots:
            if row[2]:
                plant = PLANTS[row[2]]
                if (current_time - row[3]) >= plant["time"]:
                    stealable.append(row)

        if not stealable:
            return f"🚫 {target.display_name} 的农场现在没有成熟作物，偷不到。"

        guard = await get_farm_guard(target_user_id, current_time=current_time)
        if guard:
            guard_type, _expires_at = guard
            guard_info = FARM_GUARDS.get(guard_type)
            if guard_info and random.random() < guard_info["block_rate"]:
                penalty = random.randint(guard_info["penalty_min"], guard_info["penalty_max"])
                await update_money(self.user_id, -penalty)
                return (
                    f"{guard_info['icon']} **{guard_info['name']}** 成功拦下了你！\n"
                    f"{guard_info['penalty_text']}，你损失了 **{penalty}** 喵币。"
                )

        target_plot = random.choice(stealable)
        plant_id = target_plot[2]
        plant = PLANTS[plant_id]

        if random.random() > 0.4:
            income = int(calculate_harvest(plant_id) * 0.8)
            await clear_plot(target_user_id, target_plot[1])
            await update_money(self.user_id, income)
            return f"😈 你偷到了 **{target.display_name}** 的 **{plant['name']}**！卖了 **{income}** 喵币。"

        fine = 200
        await update_money(self.user_id, -fine)
        return f"🐕 你偷菜失手，被 **{target.display_name}** 抓了个正着！罚款 **{fine}** 喵币。"


async def create_farm_dashboard(user: discord.abc.User):
    embed = await render_farm_embed(user.id, user.display_name, user.display_avatar.url)
    view = FarmDashboardView(user.id, user.display_name, user.display_avatar.url)
    return embed, view

# --- Farm Cog ---

class Farm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.crop_checker.start()

    def cog_unload(self):
        self.crop_checker.cancel()

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

        expired_guards = await get_expired_farm_guards(current_time)
        for user_id, guard_type, _expires_at in expired_guards:
            guard = FARM_GUARDS.get(guard_type)
            if not guard:
                await mark_farm_guard_notice_sent(user_id)
                await remove_farm_guard(user_id)
                continue

            try:
                user = await self.bot.fetch_user(user_id)
                if user:
                    embed = discord.Embed(title="🛡️ 护卫租赁到期提醒", color=0xE67E22)
                    embed.description = (
                        f"你租赁的 **{guard['icon']} {guard['name']}** 已经到期，农场重新暴露在偷菜风险中。\n"
                        f"记得回到农场面板重新租赁护卫哦。"
                    )
                    await user.send(embed=embed)
            except Exception:
                pass
            finally:
                await mark_farm_guard_notice_sent(user_id)
                await remove_farm_guard(user_id)

    @crop_checker.before_loop
    async def before_checker(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Farm(bot))
