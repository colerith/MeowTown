import discord


REGISTERED_ROLE_ID = 1521848592476668005


async def _resolve_member(member: discord.abc.User, guild: discord.Guild | None):
    if guild is None:
        return None

    target_member = member if isinstance(member, discord.Member) else guild.get_member(member.id)
    if target_member is None:
        try:
            target_member = await guild.fetch_member(member.id)
        except (discord.NotFound, discord.HTTPException):
            return None
    return target_member


async def grant_role_by_id(member: discord.abc.User, guild: discord.Guild | None, role_id: int, *, reason: str) -> bool:
    if guild is None:
        return False

    role = guild.get_role(role_id)
    if role is None:
        return False

    target_member = await _resolve_member(member, guild)
    if target_member is None:
        return False

    if role in target_member.roles:
        return True

    try:
        await target_member.add_roles(role, reason=reason)
        return True
    except discord.HTTPException:
        return False


async def grant_registered_role(member: discord.abc.User, guild: discord.Guild | None) -> bool:
    return await grant_role_by_id(member, guild, REGISTERED_ROLE_ID, reason="新注册喵喵自动发放身份组")
