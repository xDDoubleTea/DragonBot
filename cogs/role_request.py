from discord import (
    Guild,
    TextChannel,
    app_commands,
    Interaction,
    Member,
    Attachment,
    Role,
    errors,
    Thread,
    Embed,
)
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import Cog
from typing import Optional, Union, Set
from discord.app_commands.errors import AppCommandError, MissingPermissions
from config.models import RoleRequestStatus
from core.role_requesting_manager import (
    NoRequestableRolestoRemove,
    RoleRequestManager,
    RoleRequestChannelType,
    RoleAleardyNotRequestable,
)
from utils.embed_utils import create_themed_embed
from view.role_request_view import request_view


class RoleRequest(Cog):
    role_config = app_commands.Group(
        name="role_config",
        description="Configure the role request system for this server.",
    )

    def __init__(self, bot: commands.Bot, role_request_manager: RoleRequestManager):
        self.bot = bot
        self.role_request_manager = role_request_manager

    async def try_get_channel(
        self, guild: Guild, channel_id: int
    ) -> Optional[Union[GuildChannel, Thread]]:
        channel = guild.get_channel(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except errors.NotFound:
                return None
        return channel

    async def _get_request_sys_status(self, guild_id: int) -> RoleRequestStatus:
        request_channel_id = await self.role_request_manager.get_typed_channel_id(
            guild_id, RoleRequestChannelType.REQUEST
        )
        approval_channel_id = await self.role_request_manager.get_typed_channel_id(
            guild_id, RoleRequestChannelType.APPROVAL
        )
        if not request_channel_id and not approval_channel_id:
            return RoleRequestStatus.NOT_SET
        if not request_channel_id and approval_channel_id:
            return RoleRequestStatus.ONLY_REQUEST
        if request_channel_id and not approval_channel_id:
            return RoleRequestStatus.ONLY_APPROVE
        if not await self.role_request_manager.get_requestable_roles(guild_id=guild_id):
            return RoleRequestStatus.NO_ROLE
        return RoleRequestStatus.SET

    @Cog.listener()
    async def on_app_command_error(
        self, interaction: Interaction, error: AppCommandError
    ):
        """A global error handler for all commands in this cog."""
        if isinstance(error, MissingPermissions):
            await interaction.response.send_message(
                "你不是管理員，沒有權限使用此指令！", ephemeral=True
            )
        # Handle cases where the interaction has already been responded to
        elif isinstance(error, errors.InteractionResponded):
            await interaction.followup.send(
                "發生了一個內部錯誤，但已成功回覆。", ephemeral=True
            )
        else:
            # For other errors, you can log them or send a generic message
            print(f"An unhandled error occurred in RoleRequest cog: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"發生未知的錯誤: {error}", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"發生未知的錯誤: {error}", ephemeral=True
                )

    @role_config.command(
        name="set_channel",
        description="設置身份組審核系統的頻道",
    )
    @app_commands.describe(
        channel_type="設定的頻道種類",
        channel="你想設置的頻道，預設為觸發的頻道",
    )
    @app_commands.choices(
        channel_type=[
            # The choices are created directly from your Enum.
            # The `name` is shown to the user, and the `value` is what you receive in the code.
            app_commands.Choice(
                name="使用者申請頻道", value=RoleRequestChannelType.REQUEST.name
            ),  # "REQUEST"
            app_commands.Choice(
                name="管理員審核頻道",
                value=RoleRequestChannelType.APPROVAL.name,
            ),  # "APPROVAL"
        ]
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(
        self,
        interaction: Interaction,
        channel_type: app_commands.Choice[str],
        channel: Optional[TextChannel],
    ):
        """
        Sets a channel ID based on the enum type provided by the user's choice.
        """
        assert interaction.guild
        await interaction.response.defer(ephemeral=True)
        if not isinstance(interaction.channel, TextChannel):
            return await interaction.followup.send(
                "此指令只能在文字頻道中使用！", ephemeral=True
            )
        if not channel:
            channel = interaction.channel
        # Convert the string value from the choice back into an Enum member
        selected_type_enum = RoleRequestChannelType[channel_type.value]

        # Call your generic manager method
        await self.role_request_manager.set_typed_channel_id(
            guild_id=interaction.guild.id,
            cnl_type=selected_type_enum,
            channel_id=channel.id,
        )

        # Use the enum's friendly name for the response message
        friendly_name = channel_type.name  # e.g., "User Request Channel"
        await interaction.followup.send(
            f"{channel.mention}已經被設置為**{friendly_name}**", ephemeral=True
        )

    @role_config.command(name="add_requestable_role", description="加入可申請的身份組")
    @app_commands.guild_only()
    @app_commands.describe(role="欲加入的身份組")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_requestable_role(self, interaction: Interaction, role: Role):
        assert interaction.guild
        if (
            request_sys_status := await self._get_request_sys_status(
                guild_id=interaction.guild.id
            )
        ) not in {RoleRequestStatus.SET, RoleRequestStatus.NO_ROLE}:
            return await interaction.response.send_message(
                f"此伺服器{request_sys_status.string_repr}，請完成設置以啟用此功能",
                ephemeral=True,
            )
        await self.role_request_manager.add_requestable_role(
            guild_id=interaction.guild.id, role_id=role.id
        )
        await interaction.response.send_message(
            f"{role.mention}已成功加入可申請身份組", ephemeral=True
        )

    @role_config.command(
        name="remove_requestable_role", description="移除可申請的身份組"
    )
    @app_commands.describe(
        role="欲移除的身份組",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_requestable_role(self, interaction: Interaction, role: Role):
        assert interaction.guild
        if (
            request_sys_status := await self._get_request_sys_status(
                guild_id=interaction.guild.id
            )
        ) != RoleRequestStatus.SET:
            return await interaction.response.send_message(
                f"此伺服器{request_sys_status.string_repr}，請完成設置以啟用此功能",
                ephemeral=True,
            )
        try:
            await self.role_request_manager.remove_requestable_role(
                guild_id=interaction.guild.id, role_id=role.id
            )
        except NoRequestableRolestoRemove as e:
            return await interaction.response.send_message(e.message, ephemeral=True)
        except RoleAleardyNotRequestable as e:
            return await interaction.response.send_message(
                role.mention + e.message, ephemeral=True
            )
        await interaction.response.send_message(
            f"已經從可申請的身份組中移除{role.mention}", ephemeral=True
        )

    async def get_requestable_roles_obj(self, guild: Guild) -> Set[Role]:
        return set(
            role
            for role in map(
                guild.get_role,
                await self.role_request_manager.get_requestable_roles(
                    guild_id=guild.id
                ),
            )
            if role is not None
        )

    async def get_requestable_roles_mention(self, guild: Guild) -> str:
        returning = " ".join(
            map(
                lambda role: role.mention if role else "",
                map(
                    guild.get_role,
                    await self.role_request_manager.get_requestable_roles(
                        guild_id=guild.id
                    ),
                ),
            )
        )
        return returning if returning else "無"

    async def get_guild_status_embed(self, guild: Guild) -> Embed:
        embed = create_themed_embed(
            title="身份組申請系統狀態",
            description="伺服器：" + guild.name,
            client=self.bot,
        )
        request_channel_id = await self.role_request_manager.get_typed_channel_id(
            guild.id, RoleRequestChannelType.REQUEST
        )
        approval_channel_id = await self.role_request_manager.get_typed_channel_id(
            guild.id, RoleRequestChannelType.APPROVAL
        )
        request_cnl_name = "未知"
        approval_cnl_name = "未知"
        if not request_channel_id:
            pass
        elif request_channel := await self.try_get_channel(
            guild=guild, channel_id=request_channel_id
        ):
            request_cnl_name = request_channel.mention
        if not approval_channel_id:
            pass
        elif approval_channel := await self.try_get_channel(
            guild=guild, channel_id=approval_channel_id
        ):
            approval_cnl_name = approval_channel.mention

        embed.add_field(name="申請頻道", value=request_cnl_name, inline=False)
        embed.add_field(name="審核頻道", value=approval_cnl_name, inline=False)
        embed.add_field(
            name="可申請身份組",
            value=await self.get_requestable_roles_mention(guild=guild),
            inline=False,
        )
        return embed

    @app_commands.command(
        name="身份組申請系統狀態check_request_status",
        description="查看此伺服器申請身份組系統狀態",
    )
    @app_commands.guild_only()
    async def check_request_status(self, interaction: Interaction):
        assert interaction.guild
        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = await self.get_guild_status_embed(guild=interaction.guild)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="可申請身份組check_requestable_roles",
        description="可以申請的身份組有哪些？",
    )
    @app_commands.guild_only()
    async def check_requestable_roles(self, interaction: Interaction):
        assert interaction.guild
        await interaction.response.defer(ephemeral=True, thinking=True)
        requestable_roles_str = await self.get_requestable_roles_mention(
            guild=interaction.guild
        )
        embed = create_themed_embed(
            title="可以申請的身份組有哪些？",
            description=f"伺服器：{interaction.guild.name}",
            client=interaction.client,
        )
        embed.add_field(
            name="可以申請的身份組：", value=requestable_roles_str, inline=False
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="申請身份組request_role", description="申請前請先看過規定"
    )
    @app_commands.describe(
        role="欲申請之身分組",
        image="證明圖片",
        yt_channel_url="[選填]若申請身分組為@Youtuber或@大偶像!，請提供頻道連結",
    )
    @app_commands.guild_only()
    async def request(
        self,
        interaction: Interaction,
        role: Role,
        image: Attachment,
        yt_channel_url: Optional[str],
    ):
        assert interaction.guild and isinstance(interaction.user, Member)
        await interaction.response.defer(ephemeral=True, thinking=True)
        # This is guild only command.
        if not await self.role_request_manager.is_system_configured(
            guild_id=interaction.guild.id
        ):
            return await interaction.followup.send(
                "此伺服器還未設置申請身份組功能！如果你認為這是不合理的，請通知伺服器管理員！",
                ephemeral=True,
            )
        if not await self.role_request_manager.role_requestble(
            guild_id=interaction.guild.id, role_id=role.id
        ):
            return await interaction.followup.send(
                f"{role.mention}身分組不開放申請！", ephemeral=True
            )
        if not interaction.channel:
            return await interaction.response.send_message(
                "這裡不能使用此指令！", ephemeral=True
            )
        request_channel_id = await self.role_request_manager.get_typed_channel_id(
            guild_id=interaction.guild.id, cnl_type=RoleRequestChannelType.REQUEST
        )
        if request_channel_id and request_channel_id != interaction.channel.id:
            request_channel = await self.try_get_channel(
                guild=interaction.guild, channel_id=request_channel_id
            )
            if not request_channel:
                return await interaction.followup.send(
                    "此伺服器的申請頻道似乎被刪掉了...請通知伺服器管理員",
                    ephemeral=True,
                )
            return await interaction.followup.send(
                f"此頻道不可使用此指令！請至{request_channel.mention}頻道使用",
                ephemeral=True,
            )
        if set(interaction.user.roles) & await self.get_requestable_roles_obj(
            guild=interaction.guild
        ):
            return await interaction.followup.send(
                f"你已經有{role.mention}身份組了", ephemeral=True
            )
        approval_cnl_id = await self.role_request_manager.get_typed_channel_id(
            interaction.guild.id, RoleRequestChannelType.APPROVAL
        )
        if not approval_cnl_id:
            raise
        approval_cnl = await self.try_get_channel(
            guild=interaction.guild, channel_id=approval_cnl_id
        )
        if not approval_cnl:
            return await interaction.followup.send(
                "此伺服器的審核頻道似乎被刪掉了...請通知伺服器管理員",
                ephemeral=True,
            )
        assert isinstance(interaction.user, Member)
        embed = create_themed_embed(
            client=interaction.client,
            title="身分組申請資料",
            description=f"申請之身分組：{role.mention}\n申請人：{interaction.user.mention}\n提供之圖片：",
        )
        embed.set_image(url=image.url)
        assert embed.description
        if yt_channel_url:
            embed.description += f"\n提供YT頻道：{yt_channel_url}"
        assert isinstance(approval_cnl, TextChannel)
        view = request_view(role=role, member=interaction.user)
        await approval_cnl.send(embed=embed, view=view)
        return await interaction.followup.send(
            "已經將您提供的資料交由管理員審核！請耐心等候。\n您所提供的資料如下：",
            ephemeral=True,
            embed=embed,
        )


async def setup(client):
    await client.add_cog(
        RoleRequest(bot=client, role_request_manager=client.role_request_manager)
    )
