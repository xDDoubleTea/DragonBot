from discord import Interaction, TextChannel
import discord
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
        self.panel_message_ids = set()

    @Cog.listener(name="on_ready")
    async def on_ready(self):
        with self.ticket_manager.database_manager as db:
            all_panels = db.select(table_name="ticket_panels")
        if not all_panels:
            print("No ticket panels found in the database.")
            return
        assert isinstance(all_panels, list)
        for panel in all_panels:
            guild_id = panel.get("guild_id")
            channel_id = panel.get("channel_id")
            message_id = panel.get("message_id")
            assert guild_id and channel_id and message_id
            try:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    print(f"Cannot find guild with ID {guild_id}. Skipping.")
                    continue
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, TextChannel):
                    print(
                        f"Cannot find channel with ID {channel_id} in guild {guild_id}."
                    )
                    continue
                message = await channel.fetch_message(message_id)

                view = TicketCreationView(ticket_manager=self.ticket_manager)
                await message.edit(view=view)
                self.panel_message_ids.add(message.id)

            except discord.errors.NotFound:
                # The message was deleted
                print(
                    f"Could not find message with ID {message_id}. Deleting panel record."
                )
                with self.ticket_manager.database_manager as db:
                    db.delete("ticket_panels", {"guild_id": guild_id})
            except Exception as e:
                print(
                    f"An error occurred while re-attaching view for guild {guild_id}: {e}"
                )

    @Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, TextChannel):
            return
        with self.ticket_manager.database_manager as db:
            delete_cnl = db.select(
                table_name="ticket_panels",
                criteria={"guild_id": channel.guild.id, "channel_id": channel.id},
                fetch_one=True,
            )
            if delete_cnl:
                db.delete(
                    table_name="ticket_panels",
                    criteria={"guild_id": channel.guild.id, "channel_id": channel.id},
                )
                assert isinstance(delete_cnl, dict)
                message_id = delete_cnl["message_id"]
                if message_id in self.panel_message_ids:
                    self.panel_message_ids.remove(message_id)

    @Cog.listener(name="on_message_delete")
    async def on_message_delete(self, message):
        if message.id in self.panel_message_ids:
            with self.ticket_manager.database_manager as db:
                db.delete(
                    table_name="ticket_panels", criteria={"message_id": message.id}
                )

            self.panel_message_ids.remove(message.id)

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
            msg = await interaction.original_response()
            with self.ticket_manager.database_manager as db:
                db.insert(
                    table_name="ticket_panels",
                    data={
                        "guild_id": interaction.guild_id,
                        "channel_id": interaction.channel_id,
                        "message_id": msg.id,
                    },
                    returning_col="message_id",
                )
                self.panel_message_ids.add(msg.id)
        except AssertionError:
            return await interaction.response.send_message(
                content="Please try again.", ephemeral=True
            )


async def setup(client):
    await client.add_cog(tickets(bot=client, ticket_manager=client.ticket_manager))
