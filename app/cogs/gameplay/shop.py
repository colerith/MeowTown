# cogs/shop.py
import discord
from discord.ext import commands
from app.db.repositories.farm_repo import accelerate_farm_growth
from app.db.repositories.inventory_repo import add_item, get_items, use_item_from_db
from app.db.repositories.monopoly_repo import (
    activate_next_dice_fixed,
    get_player_position,
    get_property_owner,
    place_roadblock,
)
from app.db.repositories.user_repo import (
    equip_accessory,
    get_equipped_accessory,
    get_citizen,
    update_citizen_name,
    update_money,
)
from app.shared.data.shop_data import SHOP_ITEMS
from app.shared.data.map_data import get_map_tile

class RenameModal(discord.ui.Modal):
    def __init__(self, user_id):
        super().__init__(title="修改市民昵称")
        self.user_id = user_id
        self.add_item(discord.ui.InputText(label="新名字", max_length=20))

    async def callback(self, interaction: discord.Interaction):
        new_name = self.children[0].value
        await update_citizen_name(self.user_id, new_name)
        await interaction.response.send_message(f"✅ 改名成功！你现在叫 **{new_name}** 了。")

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    shop = discord.SlashCommandGroup("商店", "喵喵小镇购物中心")
    bag = discord.SlashCommandGroup("背包", "管理你的物品")

    @shop.command(name="列表", description="查看百货商品 (农资请去农场购买)")
    async def shop_list(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="🛍️ 喵喵百货商店", color=0xFF69B4)
        embed.set_image(url="https://i.postimg.cc/nzwYJ1Gg/shop.png")
        
        # 【修改】移除了 'farm' 分类
        categories = {"tool": "🛠️ 实用道具", "cosmetic": "👗 精品服饰"}
        
        for type_key, type_name in categories.items():
            content = ""
            for key, item in SHOP_ITEMS.items():
                if item["type"] == type_key:
                    content += f"{item['icon']} **{item['name']}** - `{item['price']} 喵币`\n> *{item['desc']}*\n"
            if content:
                embed.add_field(name=type_name, value=content, inline=False)
        
        embed.set_footer(text="提示：化肥等农用物资请在 /农场 商店 中购买")
        await ctx.respond(embed=embed)

    @shop.command(name="购买", description="购买指定物品")
    async def buy(self, ctx: discord.ApplicationContext, 
                  # 【修改】Autocomplete 过滤掉农场道具
                  物品名: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(
                      [k for k, v in SHOP_ITEMS.items() if v['type'] != 'farm']
                  ))):
        
        if 物品名 not in SHOP_ITEMS:
            await ctx.respond("🚫 商店里没有这个东西！(如果是化肥，请去农场买)", ephemeral=True)
            return

        item = SHOP_ITEMS[物品名]
        
        # 二次检查防止绕过
        if item['type'] == 'farm':
            await ctx.respond("🚜 请前往 `/农场` 打开商店购买农资用品。", ephemeral=True)
            return

        user = await get_citizen(ctx.author.id)
        if user[4] < item["price"]:
            await ctx.respond(f"🚫 余额不足！需要 **{item['price']}** 喵币。", ephemeral=True)
            return

        await update_money(ctx.author.id, -item["price"])
        await add_item(ctx.author.id, 物品名, 1)
        
        await ctx.respond(f"✅ 购买成功！你花费 **{item['price']}** 喵币购买了 **{item['icon']} {item['name']}**。")

    @bag.command(name="查看", description="查看背包中的物品")
    async def bag_view(self, ctx: discord.ApplicationContext):
        items = await get_items(ctx.author.id)
        if not items:
            await ctx.respond("🎒 你的背包空空如也。", ephemeral=True)
            return

        embed = discord.Embed(title=f"🎒 {ctx.author.display_name} 的背包", color=0x3498db)
        content = ""
        for name, count in items:
            # 即使不在商店显示的物品（如化肥），在背包里也要显示
            icon = SHOP_ITEMS.get(name, {}).get('icon', "📦")
            content += f"**{icon} {name}** x{count}\n"
        
        embed.description = content
        
        user = await get_citizen(ctx.author.id)
        acc = user[7] if user and len(user) > 7 else None
        if acc:
            embed.add_field(name="👕 当前穿戴", value=acc, inline=False)
            
        embed.set_footer(text="使用 /背包 使用 [物品名]")
        await ctx.respond(embed=embed)

    @bag.command(name="使用", description="使用或穿戴物品")
    async def use(self, ctx: discord.ApplicationContext, 
                  物品名: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(SHOP_ITEMS.keys()))):
        
        has_item = await use_item_from_db(ctx.author.id, 物品名)
        if not has_item:
            await ctx.respond(f"🚫 你背包里没有 **{物品名}**！", ephemeral=True)
            return

        item_info = SHOP_ITEMS.get(物品名, {})
        item_type = item_info.get("type", "unknown")
        
        if item_type == "cosmetic":
            old_acc_icon = await get_equipped_accessory(ctx.author.id)
            if old_acc_icon:
                for name, data in SHOP_ITEMS.items():
                    if data.get("icon") == old_acc_icon:
                        await add_item(ctx.author.id, name, 1)
                        break
            await equip_accessory(ctx.author.id, item_info['icon'])
            await ctx.respond(f"👕 你换上了 **{物品名}**！真好看！\n(旧的配饰已放回背包)")

        elif 物品名 == "改名卡":
            await ctx.send_modal(RenameModal(ctx.author.id))

        elif 物品名 in ["金坷垃", "超级金坷垃"]:
            reduce_time = 3600 if 物品名 == "金坷垃" else 18000
            await accelerate_farm_growth(ctx.author.id, reduce_time)
            await ctx.respond(f"🧪 撒下了 **{物品名}**！\n你的农场作物疯长了，距离成熟更近了！")

        elif 物品名 == "遥控骰子":
            await activate_next_dice_fixed(ctx.author.id)
            await ctx.respond("🎲 **遥控骰子**已激活！下一次在大富翁投掷必定为 6 点。")
        
        elif 物品名 == "路障":
            pos = await get_player_position(ctx.author.id)
            if pos is None:
                await add_item(ctx.author.id, 物品名, 1)
                await ctx.respond("你还没开始大富翁游戏呢！", ephemeral=True)
                return

            tile = get_map_tile(pos)
            owner_id = await get_property_owner(tile['id'])
            if tile['type'] != 'property' or owner_id != ctx.author.id:
                await add_item(ctx.author.id, 物品名, 1)
                await ctx.respond("路障只能放在 **自己的地产** 上！(道具已退还)", ephemeral=True)
                return

            await place_roadblock(tile['id'])
            await ctx.respond(f"🚧 **路障**已放置在 {tile['name']}！下一位访客将支付双倍租金。")
            
        elif 物品名 == "保释卡":
             await add_item(ctx.author.id, 物品名, 1)
             await ctx.respond("🕊️ **保释卡** 是一张被动道具，在监狱时使用 `/大富翁 保释` 会自动生效。", ephemeral=True)

        else:
            await ctx.respond(f"❓ 使用了 **{物品名}**... 好像什么也没发生。", ephemeral=True)

def setup(bot):
    bot.add_cog(Shop(bot))
