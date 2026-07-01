# cogs/cat.py
import discord
from discord.ext import commands
from app.cogs.gameplay.stock_market import (
    CompensationConfigView,
    create_stock_market_dashboard,
)
from app.cogs.gameplay.farm import create_farm_dashboard
from app.cogs.gameplay.monopoly import create_monopoly_dashboard
from app.cogs.gameplay.ranking import create_ranking_dashboard
from app.cogs.gameplay.shop import open_bag_panel, open_shop_panel
from app.cogs.gameplay.title import open_title_panel
from app.db.repositories.user_repo import create_citizen, get_citizen, get_citizen_profile_summary, update_citizen_look, update_money
from app.shared.data.cat_data import generate_cat_identity

REGISTERED_ROLE_ID = 1521848592476668005
MAGIC_REROLL_COST = 2000


def build_progress_bar(current_value, total_value, length=10):
    safe_total = max(1, int(total_value))
    ratio = min(1.0, max(0.0, current_value / safe_total))
    filled = int(round(ratio * length))
    return "█" * filled + "░" * (length - filled)


def format_large_number(value):
    abs_value = abs(float(value))
    if abs_value >= 100000000:
        return f"{value / 100000000:.2f}亿"
    if abs_value >= 10000:
        return f"{value / 10000:.2f}万"
    return f"{value:.2f}"


def pick_profile_color(level):
    if level >= 300:
        return 0xE67E22
    if level >= 150:
        return 0xE91E63
    if level >= 60:
        return 0x9B59B6
    if level >= 20:
        return 0x3498DB
    return 0x2ECC71


async def perform_magic_reroll(user_id: int):
    user = await get_citizen(user_id)
    if not user:
        return False, "no_citizen", None

    current_money = user[4]
    if current_money < MAGIC_REROLL_COST:
        return False, "insufficient", current_money

    new_species, new_pattern, _, _is_special = generate_cat_identity()
    await update_money(user_id, -MAGIC_REROLL_COST)
    await update_citizen_look(user_id, new_species, new_pattern)
    return True, user, (new_species, new_pattern)


class MagicHouseActionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="花费2000洗点", style=discord.ButtonStyle.primary, emoji="🔮")
    async def reroll_btn(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的魔法订单哦！", ephemeral=True)

        success, payload, extra = await perform_magic_reroll(interaction.user.id)
        if not success:
            if payload == "no_citizen":
                return await interaction.response.send_message("你还没有身份！", ephemeral=True)
            return await interaction.response.send_message(
                f"🔮 巫师：你的钱不够！重塑灵魂需要 **{MAGIC_REROLL_COST}** 喵币。",
                ephemeral=True,
            )

        old_user = payload
        new_species, new_pattern = extra
        embed = discord.Embed(title="🔮 魔法生效了！", description="一阵烟雾散去，你看着镜子里的自己...", color=0x9400D3)
        embed.set_image(url="https://i.postimg.cc/05WHkYNk/magic.png")
        embed.add_field(name="旧模样", value=f"{old_user[3]} {old_user[2]}", inline=True)
        embed.add_field(name="➡️", value="变身", inline=True)
        embed.add_field(name="新模样", value=f"**{new_pattern} {new_species}**", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def open_magic_house_panel(interaction: discord.Interaction, user_id: int):
    embed = discord.Embed(title="🔮 神秘魔法屋", color=0x8E44AD)
    embed.description = "巫师可以帮你重塑品种和花色，但代价不低。"
    embed.add_field(name="当前服务", value=f"洗点一次需 **{MAGIC_REROLL_COST}** 喵币。", inline=False)
    embed.add_field(name="效果说明", value="会重新随机你的品种与花色，不影响资金、称号、股票和农场。", inline=False)
    await interaction.response.send_message(embed=embed, view=MagicHouseActionView(user_id), ephemeral=True)

# --- 档案主视图 ---
class ProfileView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="👑 称号", style=discord.ButtonStyle.primary, emoji="🏷️", row=0)
    async def title_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        await open_title_panel(interaction, self.user_id)

    @discord.ui.button(label="🎒 背包", style=discord.ButtonStyle.success, emoji="🎒", row=0)
    async def bag_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        await open_bag_panel(interaction, self.user_id)

    @discord.ui.button(label="商店", style=discord.ButtonStyle.secondary, emoji="🛍️", row=0)
    async def shop_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        await open_shop_panel(interaction, self.user_id)

    @discord.ui.button(label="股市", style=discord.ButtonStyle.primary, emoji="📈", row=1)
    async def stock_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        embed, view = await create_stock_market_dashboard()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="农场", style=discord.ButtonStyle.success, emoji="🌾", row=1)
    async def farm_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        embed, view = await create_farm_dashboard(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="大富翁", style=discord.ButtonStyle.primary, emoji="🎲", row=1)
    async def monopoly_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        embed, view = await create_monopoly_dashboard(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="排行榜", style=discord.ButtonStyle.secondary, emoji="🏆", row=1)
    async def ranking_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        embed, view = await create_ranking_dashboard()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="魔法屋", style=discord.ButtonStyle.primary, emoji="🔮", row=2)
    async def magic_callback(self, button, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("这不是你的档案哦！", ephemeral=True)
        await open_magic_house_panel(interaction, self.user_id)

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

        if ctx.guild:
            role = ctx.guild.get_role(REGISTERED_ROLE_ID)
            if role:
                try:
                    await ctx.author.add_roles(role, reason="新注册喵喵自动发放身份组")
                except discord.HTTPException:
                    pass

    @citizen.command(name="档案", description="查看我的市民档案")
    async def profile(self, ctx: discord.ApplicationContext):
        summary = await get_citizen_profile_summary(ctx.author.id)
        if not summary:
            await ctx.respond("🚫 你还不是小镇居民！请先使用 `/市民 注册 [名字]` 登记。", ephemeral=True)
            return

        user = summary["citizen"]
        name = user[1]
        species = user[2]
        pattern = user[3]
        money = user[4]
        active_title = user[6] if len(user) > 6 and user[6] else "无名之辈"
        accessory = user[7] if len(user) > 7 and user[7] else ""
        citizen_level = summary["level"]
        level_score = summary["level_score"]
        progress_in_level = summary["progress_in_level"]
        progress_needed = summary["progress_needed"]
        next_threshold = summary["next_threshold"]
        progress_bar = build_progress_bar(progress_in_level, progress_needed)
        net_worth = summary["net_worth"]
        stock_value = summary["stock_value"]
        loan_amount = summary["loan_amount"]
        property_count = summary["property_count"]
        property_levels = summary["property_levels"]
        farm_plot_count = summary["farm_plot_count"]
        active_crop_count = summary["active_crop_count"]
        title_count = summary["title_count"]
        signin_count = summary["signin_count"]
        stock_share_count = summary["stock_share_count"]

        embed = discord.Embed(title="🪪 喵喵镇民档案", color=pick_profile_color(citizen_level))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_author(name=f"{ctx.author.display_name} 的市民面板", icon_url=ctx.author.display_avatar.url)

        full_name_display = f"**【{active_title}】** {name} {accessory}"
        embed.description = (
            f"{full_name_display}\n"
            f"**Lv.{citizen_level}** 资深镇民  |  品种：**{pattern}{species}**\n"
            f"`{progress_bar}` **{progress_in_level}/{progress_needed}**\n"
            f"当前成长值：**{level_score}**  |  下一级门槛：**{next_threshold}**"
        )

        embed.add_field(
            name="💰 资产概览",
            value=(
                f"现金：**{format_large_number(money)}** 喵币\n"
                f"股票市值：**{format_large_number(stock_value)}**\n"
                f"净资产：**{format_large_number(net_worth)}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="🏘️ 经营概览",
            value=(
                f"地产：**{property_count}** 块\n"
                f"地产总等级：**{property_levels}**\n"
                f"农田：**{farm_plot_count}** 块"
            ),
            inline=True,
        )
        embed.add_field(
            name="📦 收集概览",
            value=(
                f"股票持仓：**{stock_share_count}** 股\n"
                f"称号收藏：**{title_count}** 个\n"
                f"累计签到：**{signin_count}** 天"
            ),
            inline=True,
        )
        embed.add_field(
            name="🌱 当前状态",
            value=(
                f"种植中的作物：**{active_crop_count}** 块地\n"
                f"当前负债：**{format_large_number(loan_amount)}** 喵币\n"
                f"佩戴饰品：**{accessory or '暂无'}**"
            ),
            inline=False,
        )
        embed.set_footer(text="下方按钮可继续进入股市、农场、大富翁、背包、商店、称号与魔法屋")

        await ctx.respond(embed=embed, view=ProfileView(ctx.author.id))

    @citizen.command(name="公告配置", description="【仅限管理员】打开补偿公告配置面板")
    @commands.is_owner()
    async def compensation_config(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        view = CompensationConfigView()
        await ctx.followup.send(embed=view.build_preview_embed(), view=view, ephemeral=True)

    @citizen.command(name="重置股市", description="【仅限管理员】将股票价格重置到基准值")
    @commands.is_owner()
    async def reset_stock_market(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        stock_cog = self.bot.get_cog("StockMarket")
        if stock_cog is None:
            return await ctx.followup.send("🚫 股市模块未加载。", ephemeral=True)

        await stock_cog.reset_market_data()
        embed, _view = await create_stock_market_dashboard()
        await ctx.followup.send("✅ 股票价格已重置为基准值。", embed=embed, ephemeral=True)

    @citizen.command(name="补发镇民组", description="【仅限管理员】为所有已注册喵喵补发镇民身份组")
    @commands.is_owner()
    async def backfill_registered_role(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        if ctx.guild is None:
            return await ctx.followup.send("🚫 该指令只能在服务器内使用。", ephemeral=True)

        stock_cog = self.bot.get_cog("StockMarket")
        if stock_cog is None:
            return await ctx.followup.send("🚫 股市模块未加载。", ephemeral=True)

        result = await stock_cog.backfill_registered_role(ctx.guild)
        if result["role_missing"]:
            return await ctx.followup.send("🚫 未找到目标身份组。", ephemeral=True)

        await ctx.followup.send(
            f"✅ 身份组补发完成。\n新增: **{result['granted']}**\n"
            f"已拥有: **{result['skipped_existing']}**\n"
            f"不在服务器: **{result['skipped_missing']}**\n失败: **{result['failed']}**",
            ephemeral=True,
        )

    # --- 魔法屋功能 ---
    magic = discord.SlashCommandGroup("魔法屋", "神秘魔法屋")

    @magic.command(name="洗点", description="花费喵币重塑你的品种和花色")
    async def reroll(self, ctx: discord.ApplicationContext):
        success, payload, extra = await perform_magic_reroll(ctx.author.id)
        if not success and payload == "no_citizen":
            await ctx.respond("你还没有身份！", ephemeral=True)
            return
        if not success:
            await ctx.respond(f"🔮 巫师：你的钱不够！重塑灵魂需要 **{MAGIC_REROLL_COST}** 喵币。", ephemeral=True)
            return

        user = payload
        new_species, new_pattern = extra

        embed = discord.Embed(title="🔮 魔法生效了！", description="一阵烟雾散去，你看着镜子里的自己...", color=0x9400D3)
        embed.set_image(url="https://i.postimg.cc/05WHkYNk/magic.png")
        
        embed.add_field(name="旧模样", value=f"{user[3]} {user[2]}", inline=True)
        embed.add_field(name="➡️", value="变身", inline=True)
        embed.add_field(name="新模样", value=f"**{new_pattern} {new_species}**", inline=True)
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Cat(bot))
