import discord


REGISTERED_ROLE_ID = 1521848592476668005


async def grant_registered_role(member: discord.abc.User, guild: discord.Guild | None) -> bool:
    if guild is None:
        return False

    role = guild.get_role(REGISTERED_ROLE_ID)
    if role is None:
        return False

    target_member = member if isinstance(member, discord.Member) else guild.get_member(member.id)
    if target_member is None:
        try:
            target_member = await guild.fetch_member(member.id)
        except (discord.NotFound, discord.HTTPException):
            return False

    if role in target_member.roles:
        return True

    try:
        await target_member.add_roles(role, reason="新注册喵喵自动发放身份组")
        return True
    except discord.HTTPException:
        return False
