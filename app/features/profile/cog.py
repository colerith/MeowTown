import discord
from discord.ext import commands

from app.features.profile import repository
from app.features.profile import service as profile_service
from app.features.profile.ui import views as profile_ui
from app.shared.discord_roles import grant_registered_role


class ProfileCog(commands.Cog):
	def __init__(self, bot: commands.Bot, db_pool):
		self.bot = bot
		self.db_pool = db_pool

	profile = discord.SlashCommandGroup("profile", "喵喵小镇市民档案系统")

	@profile.command(name="register", description="登记身份，入住喵喵小镇！")
	async def register(self, ctx: discord.ApplicationContext, name: discord.Option(str, "给你的喵喵起个名字")):
		if await repository.get_citizen(self.db_pool, ctx.author.id):
			return await ctx.respond("🚫 你已经是小镇居民了！", ephemeral=True)

		species, pattern, money, is_special = profile_service.generate_cat_identity()
		await repository.create_citizen(self.db_pool, ctx.author.id, name, species, pattern, money)

		embed = discord.Embed(
			title="🎉 欢迎入住喵喵小镇！",
			description=f"市民登记完成，欢迎 **{name}** 加入大家庭。",
			color=0x00FF00,
		)
		embed.set_thumbnail(url=ctx.author.display_avatar.url)
		embed.add_field(name="🧬 品种", value=species, inline=True)
		embed.add_field(name="🎨 花色", value=pattern, inline=True)

		if is_special:
			embed.add_field(name="✨ 天赋异禀", value=f"触发隐藏款组合！获得启动金 **{money:.2f} 喵币**！", inline=False)
		else:
			embed.add_field(name="💰 初始资金", value=f"{money:.2f} 喵币", inline=False)

		await ctx.respond(embed=embed)
		await grant_registered_role(ctx.author, ctx.guild)

	@profile.command(name="view", description="查看我的或他人的市民档案")
	async def view(self, ctx: discord.ApplicationContext, user: discord.Option(discord.Member, "选择要查看的市民", required=False)):
		target_user = user or ctx.author

		citizen_data = await repository.get_citizen(self.db_pool, target_user.id)
		if not citizen_data:
			return await ctx.respond(f"🚫 **{target_user.display_name}** 还不是小镇居民！", ephemeral=True)

		view = profile_ui.ProfileContainerView(self.bot, self.db_pool, target_user, citizen_data)
		await ctx.respond(view=view)

	@commands.slash_command(name="title_draw", description=f"花费 {profile_service.TITLE_DRAW_COST} 喵币抽取一个称号")
	async def title_draw(self, ctx: discord.ApplicationContext):
		citizen = await repository.get_citizen(self.db_pool, ctx.author.id)
		if not citizen:
			return await ctx.respond("🚫 你还不是小镇居民！请先注册。", ephemeral=True)

		if citizen[4] < profile_service.TITLE_DRAW_COST:
			return await ctx.respond(f"🚫 余额不足！需要 **{profile_service.TITLE_DRAW_COST}** 喵币。", ephemeral=True)

		await repository.update_money(self.db_pool, ctx.author.id, -profile_service.TITLE_DRAW_COST)

		tid, title_data = profile_service.draw_random_title()
		rarity_info = profile_service.RARITY_CONFIG[title_data["rarity"]]

		is_owned = await repository.check_title_owned(self.db_pool, ctx.author.id, tid)

		embed = discord.Embed(title="🎰 称号扭蛋机", color=rarity_info["color"])
		if is_owned:
			refund = int(profile_service.TITLE_DRAW_COST / 2)
			await repository.update_money(self.db_pool, ctx.author.id, refund)
			embed.description = f"你抽到了：**【{title_data['name']}】**\n\n😕 可惜你已经有了！系统退还 **{refund}** 喵币。"
		else:
			await repository.unlock_title(self.db_pool, ctx.author.id, tid)
			embed.description = f"🎉 **恭喜！获得新称号！**\n\n🏷️ **【{title_data['name']}】**\n✨ 稀有度：**{rarity_info['name']}**"

		await ctx.respond(embed=embed)


__all__ = ["ProfileCog"]
