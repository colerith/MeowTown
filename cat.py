# cogs/cat.py
import discord
from discord.ext import commands
from discord.ui import View, Select, Button
from utils.db import (
    create_citizen, get_citizen, update_citizen_look, update_money, 
    equip_accessory, get_user_titles, get_items, add_item
)
from utils.cat_data import generate_cat_identity, SPECIAL_COMBOS
from utils.title_data import TITLES, RARITY_CONFIG
from utils.shop_data import SHOP_ITEMS 

# --- 迷你商店组件 ---
class MiniShopSelect(Select):
    def __init__(self):
        options = []
        for name, data in list(SHOP_ITEMS.items())[:25]:
            options.append(discord.SelectOption(
                label=name,
                description=f"💰{data['price']} | {data['desc'][:30]}",
                emoji=data['icon'],
                value=name
            ))
        super().__init__(placeholder="选择要购买的物品...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        item_name = self.values[0]
        item = SHOP_ITEMS[item_name]
        user_id = interaction.user.id
        
        user = await get_citizen(user_id)
        # 这里的 user[4] 可能是浮点数
        if user[4] < item['price']:
            return await interaction.response.send_message(f"🚫 余额不足！需要 **{item['price']}** 喵币。", ephemeral=True)
            
        await update_money(user_id, -item['price'])
        await add_item(user_id, item_name, 1)
        
        await interaction.response.send_message(f"✅ 成功购买 **{item['icon']} {item_name}**！\n(花费 {item['price']} 喵币)", ephemeral=True)

class MiniShopView(View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(MiniShopSelect())

# --- 档案主视图 ---
class ProfileView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="👑 称号", style=discord.ButtonStyle.primary, emoji="🏷️", row=0)
    async def title_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)

        owned_ids = await get_user_titles(self.user_id)
        if not owned_ids:
            return await interaction.response.send_message("你还没有称号！去抽奖吧。", ephemeral=True)

        user = await get_citizen(self.user_id)
        active_title = user[6] if user and len(user) > 6 else None

        embed = discord.Embed(title="🏷️ 我的称号", color=discord.Color.gold())
        desc = ""
        # 简单的排序逻辑，如果没有 rarity 可能会报错，建议加个 .get
        sorted_ids = sorted(owned_ids, key=lambda x: ["SSR", "SR", "R", "N"].index(TITLES.get(x, {}).get('rarity', 'N')))
        for tid in sorted_ids:
            data = TITLES.get(tid)
            if not data: continue
            line = f"**【{data['name']}】**"
            if active_title == data['name']: line += " ✅"
            desc += line + "\n"
        embed.description = desc
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🎒 背包", style=discord.ButtonStyle.success, emoji="🎒", row=0)
    async def bag_callback(self, button, interaction):
        if interaction.user.id != self.user_id: return

        items = await get_items(self.user_id)
        if not items:
            return await interaction.response.send_message("背包空空如也。", ephemeral=True)

        embed = discord.Embed(title="🎒 背包", color=0x3498db)
        content = ""
        for name, count in items:
            icon = SHOP_ITEMS.get(name, {}).get('icon', "📦")
            content += f"**{icon} {name}** x{count}\n"
        embed.description = content
        
        user = await get_citizen(self.user_id)
        acc = user[7] if user and len(user) > 7 else None
        if acc: embed.add_field(name="👕 穿戴中", value=acc)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="商店", style=discord.ButtonStyle.secondary, emoji="🛍️", row=0)
    async def shop_callback(self, button, interaction):
        if interaction.user.id != self.user_id: return
        
        embed = discord.Embed(title="🏪 快捷商店", description="请选择你要购买的物品：", color=0xFF69B4)
        await interaction.response.send_message(embed=embed, view=MiniShopView(), ephemeral=True)

class Cat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    citizen = discord.SlashCommandGroup("市民", "喵喵小镇市民系统")

    @citizen.command(name="注册", description="登记身份，入住喵喵小镇！(仅限初次)")
    async def register(self, ctx: discord.ApplicationContext, 
                       name: discord.Option(str, "给你的喵喵起个名字")):
        
        user_data = await get_citizen(ctx.author.id)
        if user_data:
            await ctx.respond(f"🚫 你已经是小镇居民了！你的名字是 **{user_data[1]}**。", ephemeral=True)
            return

        species, pattern, money, is_special = generate_cat_identity()
        await create_citizen(ctx.author.id, name, species, pattern, money)

        embed = discord.Embed(title="🎉 欢迎入住喵喵小镇！", description=f"市民登记完成，欢迎 **{name}** 加入大家庭。", color=0x00FF00)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🧬 品种", value=species, inline=True)
        embed.add_field(name="🎨 花色", value=pattern, inline=True)
        
        if is_special:
            embed.add_field(name="✨ 天赋异禀", value=f"触发隐藏款组合！\n获得创业启动金 **{money} 喵币**！", inline=False)
        else:
            # 这里的金额也建议保留两位小数，保持一致
            embed.add_field(name="💰 初始资金", value=f"{money} 喵币", inline=False)

        embed.set_footer(text="如果不满意长相，可以去神秘魔法屋找巫师整容哦~")
        await ctx.respond(embed=embed)

    @citizen.command(name="档案", description="查看我的市民档案")
    async def profile(self, ctx: discord.ApplicationContext):
        user = await get_citizen(ctx.author.id)
        if not user:
            await ctx.respond("🚫 你还不是小镇居民！请先使用 `/市民 注册 [名字]` 登记。", ephemeral=True)
            return
        
        name = user[1]
        species = user[2]
        pattern = user[3]
        money = user[4]
        active_title = user[6] if len(user) > 6 and user[6] else "无名之辈"
        accessory = user[7] if len(user) > 7 and user[7] else ""

        embed = discord.Embed(title=f"🆔 市民档案: {name}", color=0xFFD700)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        full_name_display = f"**【{active_title}】** {name} {accessory}"
        
        embed.add_field(name="📋 身份", value=full_name_display, inline=False)
        embed.add_field(name="👤 品种特征", value=f"【{pattern}】{species}", inline=True)
        
        # --- 修改位置在这里 ---
        # 使用 :.2f 将数字格式化为两位小数
        embed.add_field(name="💰 资产账户", value=f"**{money:.2f}** 喵币", inline=True)
        
        await ctx.respond(embed=embed, view=ProfileView(ctx.author.id))

    # --- 魔法屋功能 ---
    magic = discord.SlashCommandGroup("魔法屋", "神秘魔法屋")

    @magic.command(name="洗点", description="花费喵币重塑你的品种和花色")
    async def reroll(self, ctx: discord.ApplicationContext):
        cost = 2000
        user = await get_citizen(ctx.author.id)
        if not user:
            await ctx.respond("你还没有身份！", ephemeral=True)
            return

        current_money = user[4]
        if current_money < cost:
            # 这里的显示也可以优化
            await ctx.respond(f"🔮 巫师：你的钱不够！重塑灵魂需要 **{cost}** 喵币。", ephemeral=True)
            return

        new_species, new_pattern, _, is_special = generate_cat_identity()
        await update_money(ctx.author.id, -cost)
        await update_citizen_look(ctx.author.id, new_species, new_pattern)

        embed = discord.Embed(title="🔮 魔法生效了！", description="一阵烟雾散去，你看着镜子里的自己...", color=0x9400D3)
        embed.set_image(url="https://i.postimg.cc/05WHkYNk/magic.png")
        
        embed.add_field(name="旧模样", value=f"{user[3]} {user[2]}", inline=True)
        embed.add_field(name="➡️", value="变身", inline=True)
        embed.add_field(name="新模样", value=f"**{new_pattern} {new_species}**", inline=True)
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Cat(bot))