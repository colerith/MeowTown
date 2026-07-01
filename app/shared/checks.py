from discord.ext import commands

from app.db.repositories.user_repo import get_user


def has_cat():
	async def predicate(ctx):
		user_data = await get_user(ctx.author.id)
		if user_data:
			return True
		raise commands.CheckFailure("no_cat")

	return commands.check(predicate)


__all__ = ["has_cat"]
