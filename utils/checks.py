# utils/checks.py
from discord.ext import commands
from utils.db import get_user

# 自定义 Check 装饰器
def has_cat():
    async def predicate(ctx):
        user_data = await get_user(ctx.author.id)
        if user_data:
            return True
        raise commands.CheckFailure("no_cat") 
    return commands.check(predicate)