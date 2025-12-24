# cogs/title.py
import discord
from discord.ext import commands
from utils.db import get_citizen, update_money, unlock_title, check_title_owned, equip_user_title, get_user_titles
from utils.title_data import TITLES, RARITY_CONFIG, TITLE_DRAW_COST, draw_random_title

class Title(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    title_group = discord.SlashCommandGroup("称号", "管理你的喵喵称号")

    @title_group.command(name="抽奖", description=f"花费 {TITLE_DRAW_COST} 喵币抽取一个随机称号")
    async def draw(self, ctx: discord.ApplicationContext):
        # 1. 检查钱
        user = await get_citizen(ctx.author.id)
        if user[4] < TITLE_DRAW_COST:
            await ctx.respond(f"🚫 你的喵币不足！抽一次需要 **{TITLE_DRAW_COST}** 喵币。", ephemeral=True)
            return

        # 2. 扣钱并抽奖
        await update_money(ctx.author.id, -TITLE_DRAW_COST)
        tid, title_data = draw_random_title()
        rarity_info = RARITY_CONFIG[title_data['rarity']]
        
        # 3. 检查是否重复
        is_owned = await check_title_owned(ctx.author.id, tid)
        
        embed = discord.Embed(title="🎰 称号扭蛋机", color=rarity_info['color'])
        embed.set_image(url="https://i.postimg.cc/4dFbg1Qj/title.png")
        
        if is_owned:
            refund = int(TITLE_DRAW_COST / 2)
            await update_money(ctx.author.id, refund)
            embed.description = f"你抽到了：**【{title_data['name']}】** ({rarity_info['name']})\n\n😕 哎呀，你已经有这个称号了！\n💰 系统退还了你 **{refund}** 喵币作为安慰。"
        else:
            await unlock_title(ctx.author.id, tid)
            embed.description = f"🎉 **恭喜！你获得了一个新称号！**\n\n🏷️ **【{title_data['name']}】**\n✨ 稀有度：**{rarity_info['name']}**"
            if title_data['rarity'] == 'SSR':
                embed.description += "\n\n🚨 **传说降临！全服通告！**"
        
        await ctx.respond(embed=embed)

    @title_group.command(name="列表", description="查看你拥有的所有称号")
    async def list_titles(self, ctx: discord.ApplicationContext):
        owned_ids = await get_user_titles(ctx.author.id)
        if not owned_ids:
            await ctx.respond("你还没有任何称号！快去 `/称号 抽奖` 试试手气吧。", ephemeral=True)
            return

        # 获取当前佩戴的称号
        user = await get_citizen(ctx.author.id)

        active_title = user[5] if len(user) > 5 else None 

        embed = discord.Embed(title="🏷️ 我的称号背包", color=discord.Color.gold())
        
        # 按稀有度分类显示
        description = ""
        # 排序：SSR -> SR -> R -> N
        sorted_ids = sorted(owned_ids, key=lambda x: ["SSR", "SR", "R", "N"].index(TITLES[x]['rarity']))

        for tid in sorted_ids:
            data = TITLES[tid]
            r_name = RARITY_CONFIG[data['rarity']]['name']
            
            line = f"**【{data['name']}】** ({r_name})"
            if active_title == data['name']:
                line = f"✅ {line} (当前佩戴)"
            
            description += line + "\n"

        embed.description = description
        embed.set_footer(text="使用 /称号 佩戴 [名称] 来展示你的个性！")
        await ctx.respond(embed=embed)

    @title_group.command(name="佩戴", description="选择一个称号展示在档案上")
    async def equip(self, ctx: discord.ApplicationContext, 称号名称: str):
        # 1. 验证是否拥有
        owned_ids = await get_user_titles(ctx.author.id)
        target_tid = None
        for tid in owned_ids:
            if TITLES[tid]['name'] == 称号名称:
                target_tid = tid
                break
        
        if not target_tid:
            await ctx.respond(f"🚫 你还没有获得 **【{称号名称}】** 这个称号哦！", ephemeral=True)
            return

        # 2. 佩戴
        await equip_user_title(ctx.author.id, 称号名称)
        await ctx.respond(f"✅ 设置成功！你现在的头衔是 **【{称号名称}】**。")

def setup(bot):
    bot.add_cog(Title(bot))