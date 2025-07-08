from discord import (
    TextChannel,
    app_commands,
    Interaction,
    Member,
    Attachment,
    Role,
)
from discord.ext import commands
from discord.ext.commands import Cog
from typing import Optional
from config.constants import NOT_REQUESTABLE_ROLES_ID
from utils.embed_utils import create_themed_embed
from view.role_request_view import request_view


class RoleRequest(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="request", description="申請前請先看過規定")
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
        if role.id in NOT_REQUESTABLE_ROLES_ID:
            return await interaction.response.send_message(
                f"{role.mention}身分組不開放申請！", ephemeral=True
            )
        assert interaction.guild and interaction.channel
        if interaction.channel.id != 552116042881695746:
            return await interaction.response.send_message(
                f"此頻道不可使用此指令！請至{interaction.guild.get_channel(552116042881695746)}",
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
        if not yt_channel_url:
            embed.description += f"\n提供YT頻道：{yt_channel_url}"
        confirm_cnl = interaction.guild.get_channel(1122117193786736690)
        assert isinstance(confirm_cnl, TextChannel)
        view = request_view(role=role, member=interaction.user)
        await confirm_cnl.send(embed=embed, view=view)
        return await interaction.response.send_message(
            "已經將您提供的資料交由管理員審核！請耐心等候。\n您所提供的資料如下：",
            ephemeral=True,
            embed=embed,
        )


async def setup(client):
    await client.add_cog(RoleRequest(client))
