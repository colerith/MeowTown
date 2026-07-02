import discord
from discord.ext import commands
from discord.ui import InputText, Modal, View

from app.cogs.gameplay.cat import TOWN_GROUP, register_town_group_command


DEFAULT_ANNOUNCEMENT_TITLE = "📢 喵喵小镇公告"
DEFAULT_ANNOUNCEMENT_BODY = "这里是最新的喵喵小镇公告内容。"


def build_announcement_embed(title, body, editor_name=None):
    embed = discord.Embed(title=title, description=body, color=0xE67E22)
    if editor_name:
        embed.set_footer(text=f"最后编辑：{editor_name}")
    else:
        embed.set_footer(text="喵喵小镇公告面板")
    return embed


class AnnouncementContentModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="编辑公告标题与内容")
        self.parent_view = parent_view
        self.add_item(InputText(label="公告标题", value=parent_view.title, max_length=100))
        self.add_item(
            InputText(
                label="公告内容",
                style=discord.InputTextStyle.long,
                value=parent_view.body,
                max_length=1800,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.title = self.children[0].value.strip() or self.parent_view.title
        self.parent_view.body = self.children[1].value.strip() or self.parent_view.body
        await self.parent_view.sync_announcement(interaction)
        await self.parent_view.refresh_panel_message()
        await interaction.response.send_message("✅ 公告标题和内容已更新。", ephemeral=True)


class AnnouncementMentionModal(Modal):
    def __init__(self, parent_view):
        super().__init__(title="编辑艾特内容")
        self.parent_view = parent_view
        self.add_item(
            InputText(
                label="艾特内容",
                value=parent_view.mention_content,
                placeholder="例如：@everyone 喵喵们看这里",
                max_length=300,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.mention_content = self.children[0].value.strip()
        await self.parent_view.sync_announcement(interaction)
        await self.parent_view.refresh_panel_message()
        await interaction.response.send_message("✅ 艾特内容已更新。", ephemeral=True)


class AnnouncementEditorView(View):
    def __init__(self, target_channel, title, body, mention_enabled, mention_content):
        super().__init__(timeout=1800)
        self.target_channel = target_channel
        self.target_message = None
        self.panel_message = None
        self.title = title
        self.body = body
        self.mention_enabled = mention_enabled
        self.mention_content = mention_content or "@everyone"

    def build_panel_embed(self):
        mention_status = "开启" if self.mention_enabled else "关闭"
        embed = build_announcement_embed(self.title, self.body)
        embed.add_field(name="发布设置", value=f"艾特：**{mention_status}**", inline=True)
        embed.add_field(name="艾特内容", value=self.mention_content if self.mention_enabled else "未启用", inline=False)
        embed.add_field(
            name="正式发布状态",
            value="已发布，可继续同步更新" if self.target_message else "未发布，确认后才会发送到频道",
            inline=False,
        )
        return embed

    async def refresh_panel_message(self):
        if self.panel_message is None:
            return
        try:
            await self.panel_message.edit(embed=self.build_panel_embed(), view=self)
        except discord.HTTPException:
            pass

    async def sync_announcement(self, interaction=None):
        content = self.mention_content if self.mention_enabled else None
        if self.target_message:
            try:
                await self.target_message.edit(
                    content=content,
                    embed=build_announcement_embed(
                        self.title,
                        self.body,
                        editor_name=interaction.user.display_name if interaction else None,
                    ),
                    allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
                )
            except discord.HTTPException:
                pass
        await self.refresh_panel_message()

    async def publish_announcement(self, interaction: discord.Interaction):
        if self.target_channel is None:
            return await interaction.response.send_message("🚫 未找到可发送公告的目标频道。", ephemeral=True)

        content = self.mention_content if self.mention_enabled else None
        embed = build_announcement_embed(
            self.title,
            self.body,
            editor_name=interaction.user.display_name,
        )
        if self.target_message is None:
            self.target_message = await self.target_channel.send(
                content=content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
            )
            await interaction.response.send_message(
                f"✅ 正式公告已发布到 {self.target_channel.mention}。",
                ephemeral=True,
            )
            return

        await self.sync_announcement(interaction)
        await interaction.response.send_message("✅ 已同步到正式公告消息。", ephemeral=True)

    @discord.ui.button(label="编辑标题内容", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def edit_content_btn(self, button, interaction):
        await interaction.response.send_modal(AnnouncementContentModal(self))

    @discord.ui.button(label="切换艾特", style=discord.ButtonStyle.secondary, emoji="📣", row=0)
    async def toggle_mention_btn(self, button, interaction):
        self.mention_enabled = not self.mention_enabled
        await interaction.response.edit_message(embed=self.build_panel_embed(), view=self)

    @discord.ui.button(label="编辑艾特内容", style=discord.ButtonStyle.secondary, emoji="✏️", row=0)
    async def edit_mention_btn(self, button, interaction):
        await interaction.response.send_modal(AnnouncementMentionModal(self))

    @discord.ui.button(label="确认发布", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def publish_btn(self, button, interaction):
        await self.publish_announcement(interaction)

    @discord.ui.button(label="查看当前预览", style=discord.ButtonStyle.secondary, emoji="👀", row=1)
    async def preview_btn(self, button, interaction):
        content = self.mention_content if self.mention_enabled else None
        await interaction.response.send_message(
            content=content,
            embed=build_announcement_embed(self.title, self.body),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
        )


class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def open_announcement_editor(
        self,
        ctx: discord.ApplicationContext,
        mention_enabled: bool,
        mention_content: str,
        target_channel: discord.abc.Messageable | None,
    ):
        if target_channel is None:
            return await ctx.followup.send("🚫 未找到可发送公告的目标频道。", ephemeral=True)

        title = DEFAULT_ANNOUNCEMENT_TITLE
        body = DEFAULT_ANNOUNCEMENT_BODY
        final_mention_content = (mention_content or "@everyone").strip()

        view = AnnouncementEditorView(
            target_channel=target_channel,
            title=title,
            body=body,
            mention_enabled=mention_enabled,
            mention_content=final_mention_content,
        )
        panel_message = await ctx.followup.send(
            f"✅ 已打开公告配置面板，目标频道为 {target_channel.mention}。\n先在这里调整内容，可点击预览，确认无误后再发布正式公告。",
            embed=view.build_panel_embed(),
            view=view,
            ephemeral=True,
            wait=True,
        )
        view.panel_message = panel_message

    @TOWN_GROUP.command(name="发布公告", description="【仅限管理员】发布一条可继续编辑的公告")
    @commands.is_owner()
    async def publish_announcement(
        self,
        ctx: discord.ApplicationContext,
        是否艾特: discord.Option(bool, "是否在公告中附带艾特内容", default=False),
        艾特内容: discord.Option(str, "自定义艾特内容，可留空", required=False, default=""),
        目标频道: discord.Option(discord.TextChannel, "要发送到的频道，默认当前频道", required=False, default=None),
    ):
        await ctx.defer(ephemeral=True)
        await self.open_announcement_editor(
            ctx=ctx,
            mention_enabled=是否艾特,
            mention_content=艾特内容,
            target_channel=目标频道 or ctx.channel,
        )


def setup(bot):
    register_town_group_command(bot, Announcement.publish_announcement)
    bot.add_cog(Announcement(bot))
