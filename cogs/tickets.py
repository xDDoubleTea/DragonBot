from discord import Interaction, TextChannel
from discord.app_commands.transformers import NoneType
from discord.ext import commands
from discord.ext.commands import Context, Cog
from discord.ext.commands.hybrid import app_commands
from config.constants import (
    ticket_system_main_message,
    cus_service_role_id,
    cmd_channel_id,
)
from core.ticket_manager import TicketManager
from utils.embed_utils import create_themed_embed
from view.ticket_views import TicketCreationView


class tickets(Cog):
    def __init__(self, bot: commands.Bot, ticket_manager: TicketManager):
        self.bot = bot
        self.ticket_manager = ticket_manager

    @app_commands.command(
        name="close_ticket",
        description="Generate a button and a message to close a ticket",
    )
    async def close_ticket(self, interaction: Interaction):
        await interaction.response.send_message(
            "Click the button below to close this ticket.",
        )

    @app_commands.command(
        name="open_ticket",
        description="Generate a button and a message to open a ticket",
    )
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
