import json

from discord import app_commands, Interaction, TextChannel, Member
from discord.ext import commands
from discord.ext.commands import Cog

from core.ticket_manager import TicketManager
from config.constants import cus_service_role_id
from utils.embed_utils import create_themed_embed
from utils.giveaway_embed import giveaway_settings_to_embed
from view.giveaway_settings import GiveawaySettings
import random


class Giveaway(Cog):
    giveaway_operations = app_commands.Group(
        name="giveaway_operations", description="Giveaway settings"
    )

    def __init__(self, bot: commands.Bot, ticket_manager: TicketManager) -> None:
        self.bot = bot
        self.ticket_manager = ticket_manager

    @giveaway_operations.command(name="抽獎獎品清單", description="查看抽獎獎項")
    @app_commands.guild_only()
    @app_commands.checks.has_role(cus_service_role_id)
    async def giveaway_list(self, interaction: Interaction):
        with open("config/giveaway.json", "r") as file:
            data: dict = json.load(file)
            await interaction.response.send_message(
                embed=giveaway_settings_to_embed(
                    client=interaction.client, giveaway_settings=data
                )
            )

    @giveaway_operations.command(name="抽獎設定", description="設定抽獎獎項")
    @app_commands.guild_only()
    @app_commands.checks.has_role(cus_service_role_id)
    async def choose_set(self, interaction: Interaction):
        assert interaction.guild
        assert isinstance(interaction.user, Member)

        await interaction.response.send_modal(GiveawaySettings())

    @giveaway_operations.command(name="choose-抽獎", description="抽獎")
    @app_commands.guild_only()
    @app_commands.checks.has_role(cus_service_role_id)
    async def choose_sth(self, interaction: Interaction):
        if not isinstance(interaction.channel, TextChannel) or not (
            ticket := await self.ticket_manager.get_ticket(
                channel_id=interaction.channel.id
            )
        ):
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )
        assert interaction.guild
        assert isinstance(interaction.user, Member)

        with open("config/giveaway.json", "r") as file:
            choices = json.load(file)

        temp = [(choice, choices[choice] * 100) for choice in choices]

        res_list = random.sample(
            population=[ele[0] for ele in temp],
            counts=[int(ele[1]) for ele in temp],
            k=1,
        )
        result = res_list[0]
        members = await self.ticket_manager.get_ticket_participants_member(
            ticket_id=ticket.db_id
        )
        if not members:
            return await interaction.response.send_message(
                "Something is wrong...", ephemeral=True
            )
        members_mention = "".join([member.mention for member in members])
        return await interaction.response.send_message(
            f"{members_mention}恭喜您抽中**{result}**！"
        )

    @choose_sth.error
    async def choose_sth_error(
        self, interaction: Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingRole):
            return await interaction.response.send_message(
                "只有客服人員能夠使用此指令！", ephemeral=True
            )


async def setup(client):
    await client.add_cog(Giveaway(bot=client, ticket_manager=client.ticket_manager))
