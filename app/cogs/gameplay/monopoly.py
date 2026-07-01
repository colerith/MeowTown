import discord
import random
from discord.ext import commands
from discord.ui import View, Button, Select
from app.db.repositories.inventory_repo import add_item, get_items, use_item_from_db
from app.db.repositories.monopoly_repo import (
    activate_next_dice_fixed,
    bankrupt_player,
    buy_property,
    clear_next_dice_fixed,
    decrement_jail_turn_and_add_bad_luck,
    ensure_player,
    get_owned_property_count,
    get_owned_properties,
    get_player_position,
    get_player_state,
    get_property_owner,
    get_property_state,
    move_player,
    move_player_with_pass_go,
    pay_bail,
    pay_rent,
    place_roadblock,
    release_from_jail,
    send_player_to_jail,
    upgrade_property,
)
from app.db.repositories.user_repo import get_citizen, get_user_money, update_money
from app.features.monopoly.service import (
    build_status_text,
    calculate_property_rent,
    calculate_upgrade_cost,
    handle_bad_luck_after_event,
)
from app.shared.data.map_data import (
    MAP, MAP_SIZE, PASS_GO_SALARY, BAIL_COST, 
    get_map_tile, get_random_event, is_bad_event, get_guaranteed_good_event
)
IMG_MONOPOLY = "https://i.postimg.cc/zDtPzCfq/monopoly.png"

# --- 辅助函数：生成游戏状态 Embed ---
async def render_game_embed(user_id, user_name, avatar_url, log_text=""):
    player = await ensure_player(user_id)
    
    pos, status, turns, fixed_roll, luck = player
    current_tile = get_map_tile(pos)
    
    user = await get_citizen(user_id)
    money = user[4]

    embed = discord.Embed(title=f"🎲 喵喵都市 - {user_name}", color=0x3498db)
    embed.set_thumbnail(url=avatar_url)
    embed.set_image(url=IMG_MONOPOLY)

    status_str = build_status_text(status, turns, fixed_roll, luck)

    if log_text:
        embed.description = f"📜 **最新动态**\n{log_text}"

    embed.add_field(name="📍 当前位置", value=f"`[{pos}]` **{current_tile['name']}** {current_tile['icon']}", inline=True)
    embed.add_field(name="💰 现金", value=f"{money:.2f}", inline=True)
    embed.add_field(name="🚦 状态", value=status_str, inline=True)
    
    return embed, player

# --- UI 组件：升级地产 ---
class UpgradeSelect(Select):
    def __init__(self, properties):
        options = []
        for map_id, level, name, price in properties:
            upgrade_cost = calculate_upgrade_cost(price)
            rent = get_map_tile(map_id)['rent'][level-1]
            options.append(discord.SelectOption(
                label=f"{name} (Lv.{level})",
                description=f"升级: {upgrade_cost:.2f}币 | 当前租金: {rent:.2f}",
                value=f"{map_id}_{upgrade_cost}",
                emoji="🏗️"
            ))
        super().__init__(placeholder="选择要升级的地产...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        data_str = self.values[0].split("_")
        map_id = int(data_str[0])
        cost = float(data_str[1])

        success, _ = await upgrade_property(interaction.user.id, map_id, cost)
        if not success:
            return await interaction.response.send_message(f"🚫 资金不足！需要 {cost:.2f}", ephemeral=True)
        
        tile = get_map_tile(map_id)
        await interaction.response.send_message(f"✅ **升级成功！**\n**{tile['name']}** 变得更加豪华了，租金大幅提升！", ephemeral=True)

# --- UI 组件：道具使用 ---
class ItemSelect(Select):
    def __init__(self, items):
        options = []
        valid_items = ["遥控骰子", "路障", "出狱许可证"]
        for name, count in items:
            if name in valid_items:
                options.append(discord.SelectOption(
                    label=f"{name} (x{count})", 
                    value=name,
                    emoji="🎲" if name=="遥控骰子" else ("🚧" if name=="路障" else "🔓")
                ))
        
        if not options:
            options.append(discord.SelectOption(label="没有可用道具", value="none"))
        super().__init__(placeholder="选择要使用的道具...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        item_name = self.values[0]
        if item_name == "none": return
        
        # 道具逻辑尽量保持简单，使用 update_money 等外部函数是可以的，因为这里没有外层 DB 锁
        if item_name == "出狱许可证":
            player = await get_player_state(interaction.user.id)
            status = player[1] if player else "normal"
            if status != 'in_jail':
                return await interaction.response.send_message("你又没坐牢，用什么许可证？", ephemeral=True)

            if not await use_item_from_db(interaction.user.id, item_name):
                return await interaction.response.send_message("道具不足！", ephemeral=True)

            await release_from_jail(interaction.user.id)
            return await interaction.response.send_message("🔓 **出狱成功！** 你使用了出狱许可证，重获自由。", ephemeral=True)

        success = await use_item_from_db(interaction.user.id, item_name)
        if not success: return await interaction.response.send_message("道具不足！", ephemeral=True)

        if item_name == "遥控骰子":
            await activate_next_dice_fixed(interaction.user.id)
            msg = "🎲 **遥控骰子生效！** 下次投掷必定为 6 点。"
        elif item_name == "路障":
            pos = await get_player_position(interaction.user.id)
            tile = get_map_tile(pos)
            owner_id = await get_property_owner(tile['id'])

            if tile['type'] != 'property' or owner_id != interaction.user.id:
                await add_item(interaction.user.id, item_name)
                return await interaction.response.send_message("🚫 路障只能放在**自己的地产**上！道具已退还。", ephemeral=True)

            await place_roadblock(tile['id'])
            msg = f"🚧 **路障已放置！** {tile['name']} 的下次过路费翻倍。"
            
        await interaction.response.send_message(msg, ephemeral=True)

# --- 主控面板 ---
class MonopolyDashboardView(View):
    def __init__(self, user_id, user_name, avatar_url):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_info = (user_name, avatar_url)
        self.log = "欢迎来到喵喵都市！请点击投骰子开始冒险。"
        self.current_tile_price = 0

    async def refresh_ui(self, interaction):
        embed, player = await render_game_embed(self.user_id, *self.user_info, log_text=self.log)
        pos, status, _, _, _ = player
        
        can_buy = False
        tile = get_map_tile(pos)
        
        if status == 'normal' and tile['type'] == 'property':
            owner_id = await get_property_owner(tile['id'])
            if owner_id is None:
                can_buy = True
                self.current_tile_price = tile['price']
        
        self.children[0].disabled = False 
        self.children[1].disabled = not can_buy
        if can_buy:
            self.children[1].label = f"购买 ({self.current_tile_price})"
            self.children[1].style = discord.ButtonStyle.success
        else:
            self.children[1].label = "购买"
            self.children[1].style = discord.ButtonStyle.secondary

        self.children[5].disabled = (status != 'in_jail')

        try:
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            print(f"UI Refresh Error: {e}")

    @discord.ui.button(label="投骰子", style=discord.ButtonStyle.primary, emoji="🎲", row=0)
    async def roll_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        # 1. 获取玩家数据 (包括 bad_luck_count)
        player = await ensure_player(self.user_id)
        
        user_id = player[0]
        current_pos = player[1]
        status = player[2]
        turns_left = player[3]
        fixed_roll = player[4]
        
        bad_luck = player[5] if len(player) > 5 else 0 

        self.log = "" 
        
        # 2. 坐牢逻辑
        if status == 'in_jail':
            if turns_left > 0:
                await decrement_jail_turn_and_add_bad_luck(user_id, turns_left)
                self.log = f"👮 **禁闭中...** (剩余 {turns_left - 1} 回合)\n🌩️ 坐牢太惨了，霉运值 +1"
                await self.refresh_ui(interaction)
                return
            await release_from_jail(user_id)
            self.log += "🔓 **刑满释放！** 重获自由！\n"
        
        # 3. 投掷与移动
        roll = fixed_roll if fixed_roll > 0 else random.randint(1, 6)
        
        if fixed_roll > 0:
            await clear_next_dice_fixed(user_id)

        new_pos, passed_go = await move_player_with_pass_go(user_id, current_pos, roll, MAP_SIZE, PASS_GO_SALARY)
        if passed_go:
            self.log += f"💰 经过起点，领取工资 {PASS_GO_SALARY}！\n"

        tile = get_map_tile(new_pos)
        self.log += f"🎲 投出 **{roll}** 点 ➜ 🏃 来到 **{tile['name']}**"
        
        # --- 事件处理 (含保底逻辑) ---
        new_bad_luck = bad_luck # 临时变量，计算完后统一写入

        if tile['type'] == 'property':
            # 踩到别人的地算倒霉吗？算！踩空地或者自己的地算运气好/中性
            # 这里简化处理：踩到别人的地且付了租金，霉运+1
            prop = await get_property_state(tile['id'])

            if not prop:
                self.log += f"\n🏷️ 空地 (价格 {tile['price']:.2f})，可购买。"
                new_bad_luck = 0
            elif prop[0] == user_id:
                self.log += f"\n🏠 回到自己的地盘。"
                new_bad_luck = max(0, new_bad_luck - 1)
            else:
                rent = calculate_property_rent(tile, prop[1], prop[2])
                try:
                    owner_name = (await interaction.client.fetch_user(prop[0])).display_name
                except Exception:
                    owner_name = "神秘人"

                self.log += f"\n💸 支付租金 **{rent:.2f}** 给 {owner_name}。"
                if prop[2] == 'roadblock':
                    self.log += " (🚧路障!)"

                await pay_rent(user_id, prop[0], rent, map_id=tile['id'], clear_roadblock=(prop[2] == 'roadblock'))

                new_bad_luck += 1

        elif tile['type'] in ['chance', 'destiny']:
            # --- 保底核心逻辑 ---
            event = None
            is_guaranteed = False
            
            # 如果霉运值 >= 3，触发保底
            if bad_luck >= 3:
                event = get_guaranteed_good_event(tile['type'])
                is_guaranteed = True
                new_bad_luck = 0 # 触发保底后清零
                self.log += "\n✨ **触底反弹！** (你太倒霉了，幸运女神眷顾了你)"
            else:
                event = get_random_event(tile['type'])
                # 根据结果调整霉运值
                new_bad_luck = handle_bad_luck_after_event(new_bad_luck, is_bad_event(event))

            if event:
                self.log += f"\n📜 **{event['text']}**"
                
                # ... (原来的事件处理代码，逻辑完全一样，为了简洁我只写关键变化) ...
                if event['type'] == 'money':
                    val = event['value']
                    await update_money(user_id, val)
                
                elif event['type'] == 'item':
                    await add_item(user_id, event['value'])
                    self.log += f"\n🎒 获得道具：{event['value']}"
                
                elif event['type'] == 'go_to_jail':
                    await self._go_jail(user_id)
                    new_bad_luck += 1 # 再次确认增加
                    self.log += "\n🚓 警车来了！"

                elif event['type'] == 'move':
                    step = event['value']
                    final_pos = (new_pos + step) % MAP_SIZE
                    await move_player(user_id, final_pos)
                    target_tile = get_map_tile(final_pos)
                    self.log += f"\n➡️ 移动到了 **{target_tile['name']}**"

                elif event['type'] == 'move_to':
                    final_pos = event['value']
                    await move_player(user_id, final_pos)
                    target_tile = get_map_tile(final_pos)
                    self.log += f"\n🚀 传送到了 **{target_tile['name']}**"
                
                elif event['type'] in ['pay_per_property', 'gain_per_property']:
                    count = await get_owned_property_count(user_id)
                    total_amount = count * event['value']
                    if event['type'] == 'pay_per_property':
                        await update_money(user_id, -total_amount)
                        self.log += f"\n📉 支付了 {total_amount:.2f} 维护费。"
                    else:
                        await update_money(user_id, total_amount)
                        self.log += f"\n📈 获得了 {total_amount:.2f} 收益。"

        elif tile['type'] == 'tax':
            self.log += f"\n📉 缴纳税款 **{tile['fee']:.2f}**。"
            await update_money(user_id, -tile['fee'])

        elif tile['type'] == 'go_to_jail':
            self.log += "\n🚓 坏事做尽，被带到了禁闭室！"
            await self._go_jail(user_id)

        # 检查是否因为这回合的操作破产了
        await self.check_bankruptcy(user_id)
        
        await self.refresh_ui(interaction)

    @discord.ui.button(label="购买", style=discord.ButtonStyle.secondary, emoji="🏠", row=0, disabled=True)
    async def buy_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        pos = await get_player_position(self.user_id)
        tile = get_map_tile(pos)

        success, reason = await buy_property(self.user_id, tile['id'], tile['price'])
        if not success:
            if reason == "owned":
                self.log = "❌ 手慢了！这块地刚刚被买走了。"
                await self.refresh_ui(interaction)
                return
            if reason == "insufficient":
                await interaction.response.send_message("资金不足！", ephemeral=True)
                return

        self.log = f"🎉 **恭喜！**\n你花费 {tile['price']:.2f} 喵币买下了 **{tile['name']}**！"
             
        await self.refresh_ui(interaction)

    @discord.ui.button(label="资产", style=discord.ButtonStyle.secondary, emoji="🏰", row=0)
    async def asset_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        rows = await get_owned_properties(self.user_id)
        
        if not rows:
            return await interaction.response.send_message("🚫 你名下没有任何房产。", ephemeral=True)
        
        props_data = []
        for map_id, level in rows:
            tile = get_map_tile(map_id)
            if level < 5: 
                props_data.append((map_id, level, tile['name'], tile['price']))
        
        if not props_data:
            return await interaction.response.send_message("🚫 所有房产均已升至最高级！", ephemeral=True)

        view = View()
        view.add_item(UpgradeSelect(props_data[:25])) 
        await interaction.response.send_message("🏗️ 请选择要升级的地产：", view=view, ephemeral=True)

    @discord.ui.button(label="背包", style=discord.ButtonStyle.secondary, emoji="🎒", row=1)
    async def bag_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return
        items = await get_items(self.user_id)
        if not items: return await interaction.response.send_message("🎒 背包空空如也。", ephemeral=True)
        
        view = View()
        view.add_item(ItemSelect(items))
        await interaction.response.send_message("🎒 选择要使用的道具：", view=view, ephemeral=True)

    @discord.ui.button(label="刷新", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, button, interaction):
        await self.refresh_ui(interaction)

    @discord.ui.button(label="保释", style=discord.ButtonStyle.danger, emoji="💸", row=1, disabled=True)
    async def bail_btn(self, button, interaction):
        if interaction.user.id != self.user_id: return

        success, _ = await pay_bail(self.user_id, BAIL_COST)
        if not success:
            return await interaction.response.send_message(f"🚫 钱不够！保释需要 {BAIL_COST}。", ephemeral=True)
             
        self.log = "🔓 **保释成功！** 你自由了。"
        await self.refresh_ui(interaction)

    # 破产检查辅助函数
    async def check_bankruptcy(self, user_id):
        money = await get_user_money(user_id)
        if money < 0:
            self.log += f"\n🚨 **破产清算！** 资金不足 ({money:.2f})，所有房产充公。"
            await bankrupt_player(user_id)

    async def _go_jail(self, user_id):
        await send_player_to_jail(user_id)


async def create_monopoly_dashboard(user: discord.abc.User):
    embed, player = await render_game_embed(user.id, user.display_name, user.display_avatar.url)
    view = MonopolyDashboardView(user.id, user.display_name, user.display_avatar.url)
    if len(player) > 1:
        status = player[1]
        view.children[5].disabled = (status != "in_jail")
    return embed, view

class Monopoly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Monopoly(bot))
