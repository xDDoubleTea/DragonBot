from discord import Interaction, TextChannel
from discord.ext import commands
from discord.ext.commands import Cog
from discord.ext.commands.hybrid import app_commands
from config.constants import (
    ticket_system_main_message,
    cus_service_role_id,
    cmd_channel_id,
)
from core.ticket_manager import TicketManager
from utils.embed_utils import create_themed_embed
from view.ticket_views import TicketCloseToggleView, TicketCreationView


class tickets(Cog):
    def __init__(self, bot: commands.Bot, ticket_manager: TicketManager):
        self.bot = bot
        self.ticket_manager = ticket_manager

    @app_commands.command(
        name="close_ticket",
        description="將生成一個新的關閉頻道訊息，只能在客服頻道中且只能被客服人員使用。",
    )
    @app_commands.checks.has_role(cus_service_role_id)
    async def close_ticket(self, interaction: Interaction):
        try:
            assert interaction.channel and isinstance(interaction.channel, TextChannel)
            assert self.ticket_manager.is_ticket_channel(
                channel_id=interaction.channel.id
            )
            # First send the message
            await interaction.response.send_message(
                "新的關閉頻道按鈕",
                view=TicketCloseToggleView(self.ticket_manager),
            )
            # Delete the old close message, if any
            old_close_msg_id = await self.ticket_manager.get_close_msg_id(
                interaction.channel.id
            )
            if old_close_msg_id:
                msg = interaction.channel.get_partial_message(old_close_msg_id)
                assert msg
                await msg.edit(view=None)
            # Set the new close message id to the response message
            msg = await interaction.original_response()
            assert msg
            return await self.ticket_manager.set_close_msg_id(
                interaction.channel.id, msg.id
            )

        except AssertionError:
            await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )

    @close_ticket.error
    async def close_ticket_err(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingRole):
            return interaction.response.send_message("你不是客服人員！", ephemeral=True)

    @app_commands.command(
        name="open_ticket",
        description="將生成一個新的開啟客服頻道之訊息。需要管理員權限才可使用。",
    )
    @app_commands.default_permissions()
    async def open_ticket(self, interaction: Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                content="Please try again.", ephemeral=True
            )
        cus_service_role = interaction.guild.get_role(cus_service_role_id)
        cmd_channel = interaction.guild.get_channel_or_thread(cmd_channel_id)
        if cus_service_role is None or cmd_channel is None:
            return await interaction.response.send_message(
                content="Please try again.", ephemeral=True
            )
        try:
            assert isinstance(cmd_channel, TextChannel)
            view = TicketCreationView(ticket_manager=self.ticket_manager)
            embed = create_themed_embed(
                title="【DRAGON龍龍】客服專區",
                description="請點下方按鈕開啟客服頻道，點擊後會開啟一個只有您跟客服人員才看的到的私人頻道，即可至開啟的頻道傳送訊息，謝謝您。",
            )
            embed.url = "https://dragonshop.org/"
            embed.set_image(url="https://i.imgur.com/AgKFvBT.png")
            await interaction.response.send_message(
                content=ticket_system_main_message(
                    role=cus_service_role, cmd_channel=cmd_channel
                ),
                view=view,
                embed=embed,
            )
        except AssertionError:
            return await interaction.response.send_message(
                content="Please try again.", ephemeral=True
            )


async def setup(client):
    await client.add_cog(tickets(bot=client, ticket_manager=client.ticket_manager))
