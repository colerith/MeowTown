import discord
from discord.ext import commands
from discord.ui import Select, View

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
from app.shared.data.map_data import get_map_tile
from app.shared.data.shop_data import SHOP_ITEMS

SHOP_IMAGE = "https://i.postimg.cc/nzwYJ1Gg/shop.png"


class RenameModal(discord.ui.Modal):
    def __init__(self, user_id):
        super().__init__(title="修改市民昵称")
        self.user_id = user_id
        self.add_item(discord.ui.InputText(label="新名字", max_length=20))

    async def callback(self, interaction: discord.Interaction):
        new_name = self.children[0].value
        await update_citizen_name(self.user_id, new_name)
        await interaction.response.send_message(f"✅ 改名成功！你现在叫 **{new_name}** 了。", ephemeral=True)


def build_shop_embed():
    embed = discord.Embed(title="🛍️ 喵喵百货商店", color=0xFF69B4)
    embed.set_image(url=SHOP_IMAGE)

    categories = {"tool": "🛠️ 实用道具", "cosmetic": "👗 精品服饰"}
    for type_key, type_name in categories.items():
        content = ""
        for item in SHOP_ITEMS.values():
            if item["type"] == type_key:
                content += f"{item['icon']} **{item['name']}** - `{item['price']} 喵币`\n> *{item['desc']}*\n"
        if content:
            embed.add_field(name=type_name, value=content, inline=False)

    embed.set_footer(text="提示：农资用品请前往农场面板购买")
    return embed


async def build_bag_embed(user_id, display_name):
    items = await get_items(user_id)
    if not items:
        return None

    embed = discord.Embed(title=f"🎒 {display_name} 的背包", color=0x3498DB)
    content = ""
    for name, count in items:
        icon = SHOP_ITEMS.get(name, {}).get("icon", "📦")
        content += f"**{icon} {name}** x{count}\n"
    embed.description = content

    user = await get_citizen(user_id)
    acc = user[7] if user and len(user) > 7 else None
    if acc:
        embed.add_field(name="👕 当前穿戴", value=acc, inline=False)
    return embed


class ShopBuySelect(Select):
    def __init__(self, user_id):
        self.user_id = user_id
        options = []
        for name, item in SHOP_ITEMS.items():
            if item["type"] == "farm":
                continue
            options.append(
                discord.SelectOption(
                    label=name,
                    value=name,
                    description=f"💰{item['price']} | {item['desc'][:40]}",
                    emoji=item["icon"],
                )
            )
        super().__init__(placeholder="选择要购买的物品...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的商店面板。", ephemeral=True)

        item_name = self.values[0]
        item = SHOP_ITEMS[item_name]
        user = await get_citizen(self.user_id)
        if user[4] < item["price"]:
            return await interaction.response.send_message(
                f"🚫 余额不足！需要 **{item['price']}** 喵币。",
                ephemeral=True,
            )

        await update_money(self.user_id, -item["price"])
        await add_item(self.user_id, item_name, 1)
        await interaction.response.send_message(
            f"✅ 购买成功！你获得了 **{item['icon']} {item_name}**。",
            ephemeral=True,
        )


class ShopView(View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.add_item(ShopBuySelect(user_id))


class BagUseSelect(Select):
    def __init__(self, user_id, items):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=name,
                value=name,
                description=f"当前拥有 {count} 个",
                emoji=SHOP_ITEMS.get(name, {}).get("icon", "📦"),
            )
            for name, count in items
        ]
        super().__init__(placeholder="选择要使用的物品...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的背包面板。", ephemeral=True)

        item_name = self.values[0]
        has_item = await use_item_from_db(self.user_id, item_name)
        if not has_item:
            return await interaction.response.send_message(f"🚫 你背包里没有 **{item_name}**！", ephemeral=True)

        item_info = SHOP_ITEMS.get(item_name, {})
        item_type = item_info.get("type", "unknown")

        if item_type == "cosmetic":
            old_acc_icon = await get_equipped_accessory(self.user_id)
            if old_acc_icon:
                for name, data in SHOP_ITEMS.items():
                    if data.get("icon") == old_acc_icon:
                        await add_item(self.user_id, name, 1)
                        break
            await equip_accessory(self.user_id, item_info["icon"])
            return await interaction.response.send_message(
                f"👕 你换上了 **{item_name}**！旧配饰已放回背包。",
                ephemeral=True,
            )

        if item_name == "改名卡":
            return await interaction.response.send_modal(RenameModal(self.user_id))

        if item_name in ["金坷垃", "超级金坷垃"]:
            reduce_time = 3600 if item_name == "金坷垃" else 18000
            await accelerate_farm_growth(self.user_id, reduce_time)
            return await interaction.response.send_message(
                f"🧪 撒下了 **{item_name}**！你的农场作物距离成熟更近了。",
                ephemeral=True,
            )

        if item_name == "遥控骰子":
            await activate_next_dice_fixed(self.user_id)
            return await interaction.response.send_message(
                "🎲 **遥控骰子**已激活！下一次在大富翁投掷必定为 6 点。",
                ephemeral=True,
            )

        if item_name == "路障":
            pos = await get_player_position(self.user_id)
            if pos is None:
                await add_item(self.user_id, item_name, 1)
                return await interaction.response.send_message("你还没开始大富翁游戏呢！", ephemeral=True)

            tile = get_map_tile(pos)
            owner_id = await get_property_owner(tile["id"])
            if tile["type"] != "property" or owner_id != self.user_id:
                await add_item(self.user_id, item_name, 1)
                return await interaction.response.send_message(
                    "路障只能放在 **自己的地产** 上！(道具已退还)",
                    ephemeral=True,
                )

            await place_roadblock(tile["id"])
            return await interaction.response.send_message(
                f"🚧 **路障**已放置在 {tile['name']}！下一位访客将支付双倍租金。",
                ephemeral=True,
            )

        await interaction.response.send_message(f"❓ 使用了 **{item_name}**，暂时没有更多效果。", ephemeral=True)


class BagView(View):
    def __init__(self, user_id, items):
        super().__init__(timeout=300)
        self.add_item(BagUseSelect(user_id, items))


async def open_shop_panel(interaction: discord.Interaction, user_id: int):
    await interaction.response.send_message(embed=build_shop_embed(), view=ShopView(user_id), ephemeral=True)


async def open_bag_panel(interaction: discord.Interaction, user_id: int):
    items = await get_items(user_id)
    if not items:
        return await interaction.response.send_message("🎒 你的背包空空如也。", ephemeral=True)

    embed = await build_bag_embed(user_id, interaction.user.display_name)
    await interaction.response.send_message(embed=embed, view=BagView(user_id, items), ephemeral=True)


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


def setup(bot):
    bot.add_cog(Shop(bot))
