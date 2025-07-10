from discord import Interaction, Member, TextChannel, User, Message
import discord
from discord.app_commands import MissingRole
from discord.app_commands.errors import AppCommandError
from discord.ext import commands
from discord.ext.commands import Cog
from discord.ext.commands.hybrid import app_commands
from config.canned_response import ReplyKeys
from config.constants import (
    My_user_id,
    ticket_system_main_message,
    cus_service_role_id,
    cmd_channel_id,
    ericdragon_user_id,
    epic_dragon_role_id,
    admin_role_id,
    rare_dragon_role_id,
    app_id,
)
from config.models import CloseMessageType, TicketStatus
from config.canned_response import CANNED_RESPONSES
from core.exceptions import ChannelNotTicket, NoParticipants, TicketNotFound
from core.ticket_manager import TicketManager
from utils.embed_utils import create_themed_embed
from view.ticket_views import (
    TicketAfterClose,
    TicketCloseToggleView,
    TicketCloseView,
    TicketCreationView,
)
from typing import List, Union
from utils.transformers import CannedResponseTransformer


class tickets(Cog):
    def __init__(self, bot: commands.Bot, ticket_manager: TicketManager):
        self.bot = bot
        self.ticket_manager = ticket_manager
        self.panel_message_ids = set()

    async def restore_ticket_panel(self):
        all_panels = await self.ticket_manager.database_manager.select(
            table_name=self.ticket_manager.ticket_panels_table_name
        )
        print("Restoring ticket panels....")
        if not all_panels:
            print("No ticket panels found in the database.")
        else:
            assert isinstance(all_panels, list)
            for panel in all_panels:
                guild_id = panel.get("guild_id")
                channel_id = panel.get("channel_id")
                message_id = panel.get("message_id")
                assert guild_id and channel_id and message_id
                try:
                    print(f"Restoring panel for guild with ID {guild_id}")
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
                    await self.ticket_manager.database_manager.delete(
                        "ticket_panels", {"guild_id": guild_id}
                    )
                except Exception as e:
                    print(
                        f"An error occurred while re-attaching view for guild {guild_id}: {e}"
                    )
        print("Done!")

    @Cog.listener(name="on_ready")
    async def on_ready(self):
        await self.restore_ticket_panel()
        print("Restoring all close buttons...")
        all_tickets = await self.ticket_manager.database_manager.select(
            table_name="tickets"
        )
        if not all_tickets:
            print("No tickets found in database, skipping...")
        else:
            assert isinstance(all_tickets, list)
            close_view: List[
                Union[
                    type[TicketCloseToggleView],
                    type[TicketCloseView],
                    type[TicketAfterClose],
                ]
            ] = [TicketCloseToggleView, TicketCloseView, TicketAfterClose]
            deleted_tickets_id = []
            for ticket in all_tickets:
                ticket = await self.ticket_manager.get_ticket(ticket_id=ticket["id"])
                assert ticket
                close_msg_id = ticket.close_msg_id
                close_msg_type = ticket.close_msg_type
                guild_id = ticket.guild_id
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    try:
                        guild = await self.bot.fetch_guild(guild_id)
                    except discord.errors.NotFound:
                        print(
                            f"Could not find the guild with guild id {guild_id}, skipping..."
                        )
                        continue
                channel_id = ticket.channel_id
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, TextChannel):
                    # The channel has been deleted, so we can remove the ticket from the database.
                    try:
                        channel = await guild.fetch_channel(channel_id)
                        if not isinstance(channel, TextChannel):
                            raise TicketNotFound(
                                f"Channel with ID {channel_id} is not a TextChannel."
                            )
                    except discord.errors.NotFound:
                        print(
                            f"Could not find the channel with id {channel_id} in guild {guild_id}. Deleting ticket from database."
                        )
                        await self.ticket_manager.database_manager.delete(
                            table_name="tickets", criteria={"id": ticket.db_id}
                        )
                        deleted_tickets_id.append(ticket.db_id)
                        continue
                    except TicketNotFound as e:
                        print(f"Error: {e}. Deleting ticket from database.")
                        await self.ticket_manager.database_manager.delete(
                            table_name="tickets", criteria={"id": ticket.db_id}
                        )
                        deleted_tickets_id.append(ticket.db_id)
                        continue
                try:
                    message = await channel.fetch_message(close_msg_id)
                    print(f"Restoring close buttons in ticket with id {ticket.db_id}")
                    view = close_view[CloseMessageType(close_msg_type)](
                        ticket_manager=self.ticket_manager,
                    )
                    await message.edit(view=view)
                    print(f"Setting channel name for ticket with id {ticket.db_id}")
                    await self.ticket_manager.set_ticket_status(
                        ticket=ticket,
                        new_status=ticket.status,
                        ticket_channel=channel,
                    )
                except discord.errors.NotFound:
                    print(
                        f"Could not find the closing message with id {close_msg_id}. Resending the close button message."
                    )
                    # Send new close button message
                except Exception as e:
                    print("Error: ", e)
            for ticket_id in deleted_tickets_id:
                await self.ticket_manager.database_manager.delete(
                    table_name="tickets", criteria={"id": ticket_id}
                )
        print("Done!")

    @staticmethod
    def _admin_mentioned(message: Message) -> bool:
        return bool(
            (len(message.raw_mentions) or len(message.raw_role_mentions))
            and (
                cus_service_role_id in message.raw_role_mentions
                or app_id in message.raw_mentions
                or ericdragon_user_id in message.raw_mentions
                or My_user_id in message.raw_mentions
                or admin_role_id in message.raw_role_mentions
                or epic_dragon_role_id in message.raw_role_mentions
                or rare_dragon_role_id in message.raw_role_mentions
            )
        )

    @Cog.listener(name="on_message")
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        ticket = await self.ticket_manager.get_ticket(channel_id=message.channel.id)
        if not ticket:
            # We don't care about the message sent outside of tickets.
            return

        assert (
            message.guild
            and isinstance(message.channel, TextChannel)
            and isinstance(message.author, Member)
        )
        # Because ticket is a TextChannel in a Guild, AssertionError won't be raised
        cus_service_role = message.guild.get_role(cus_service_role_id)
        if (
            ticket.status == TicketStatus.OPEN
            and cus_service_role in message.author.roles
        ):
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.IN_PROGRESS
            )
        if self._admin_mentioned(message=message):
            await message.channel.send(
                "你好！我們已收到你的訊息，感謝你與我們聯繫。待上線後將會回答您的問題~"
            )

    @Cog.listener(name="on_message_edit")
    async def on_message_edit(self, before: Message, after: Message):
        if before.author.bot:
            return
        ticket = await self.ticket_manager.get_ticket(channel_id=after.channel.id)
        if not ticket:
            # We don't care about the message sent outside of tickets.
            return

        assert (
            after.guild
            and isinstance(after.channel, TextChannel)
            and isinstance(after.author, Member)
        )
        # Because ticket is a TextChannel in a Guild, AssertionError won't be raised
        cus_service_role = after.guild.get_role(cus_service_role_id)
        if (
            ticket.status == TicketStatus.OPEN
            and cus_service_role in after.author.roles
        ):
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.IN_PROGRESS
            )
        if self._admin_mentioned(message=after) and not self._admin_mentioned(
            message=before
        ):
            await after.channel.send(
                "你好！我們已收到你的訊息，感謝你與我們聯繫。待上線後將會回答您的問題~"
            )

    @Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, TextChannel):
            return
        delete_cnl = await self.ticket_manager.database_manager.select(
            table_name=self.ticket_manager.ticket_panels_table_name,
            criteria={"guild_id": channel.guild.id, "channel_id": channel.id},
            fetch_one=True,
        )
        if delete_cnl:
            await self.ticket_manager.database_manager.delete(
                table_name=self.ticket_manager.ticket_panels_table_name,
                criteria={"guild_id": channel.guild.id, "channel_id": channel.id},
            )
            assert isinstance(delete_cnl, dict)
            message_id = delete_cnl["message_id"]
            if message_id in self.panel_message_ids:
                self.panel_message_ids.remove(message_id)

    @Cog.listener(name="on_message_delete")
    async def on_message_delete(self, message):
        if message.id in self.panel_message_ids:
            await self.ticket_manager.database_manager.delete(
                table_name=self.ticket_manager.ticket_panels_table_name,
                criteria={"message_id": message.id},
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
            return await self.ticket_manager.set_close_msg(
                channel_id=interaction.channel.id,
                close_msg_id=msg.id,
                close_msg_type=CloseMessageType.CLOSE_TOGGLE,
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
    @app_commands.checks.has_permissions(administrator=True)
    async def open_ticket(self, interaction: Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                content="Please try again.", ephemeral=True
            )
        cus_service_role = interaction.guild.get_role(cus_service_role_id)
        cmd_channel = interaction.guild.get_channel(cmd_channel_id)
        if cus_service_role is None or cmd_channel is None:
            return await interaction.response.send_message(
                content="Please try again.", ephemeral=True
            )
        if not isinstance(interaction.channel, TextChannel):
            return await interaction.response.send_message(
                "You should put this message in a text channel."
            )
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            assert isinstance(cmd_channel, TextChannel)
            panel = await self.ticket_manager.database_manager.select(
                table_name=self.ticket_manager.ticket_panels_table_name,
                criteria={"guild_id": interaction.guild.id},
                fetch_one=True,
            )
            if panel:
                assert isinstance(panel, dict)
                panel_cnl = interaction.guild.get_channel(panel["channel_id"])
                assert isinstance(panel_cnl, TextChannel)
                try:
                    panel_msg = await panel_cnl.fetch_message(panel["message_id"])
                    return await interaction.followup.send(
                        content=f"There should only exist one open message for each guild. The url of the open message in your guild is {panel_msg.jump_url}"
                    )
                except discord.errors.NotFound:
                    view = TicketCreationView(ticket_manager=self.ticket_manager)
                    embed = create_themed_embed(
                        title="【DRAGON龍龍】客服專區",
                        description="請點下方按鈕開啟客服頻道，點擊後會開啟一個只有您跟客服人員才看的到的私人頻道，即可至開啟的頻道傳送訊息，謝謝您。",
                    )
                    embed.url = "https://dragonshop.org/"
                    embed.set_image(url="https://i.imgur.com/AgKFvBT.png")
                    await interaction.followup.send(
                        content=ticket_system_main_message(
                            role=cus_service_role, cmd_channel=cmd_channel
                        ),
                        view=view,
                        embed=embed,
                    )
                    msg = await interaction.original_response()
                    await self.ticket_manager.database_manager.update(
                        table_name=self.ticket_manager.ticket_panels_table_name,
                        data={
                            "channel_id": interaction.channel_id,
                            "message_id": msg.id,
                        },
                        criteria={"guild_id": interaction.guild_id},
                    )
                    self.panel_message_ids.add(msg.id)

        except AssertionError:
            return await interaction.followup.send(
                content="Please try again.", ephemeral=True
            )

    @app_commands.command(
        name="add_participant",
        description="將使用者加入客服頻道，需要客服人員身份組才可使用。",
    )
    @app_commands.checks.has_role(cus_service_role_id)
    async def add_participant(self, interaction: Interaction, user: User):
        try:
            if user.bot:
                return await interaction.response.send_message(
                    content="你不能將機器人加入客服頻道。", ephemeral=True
                )
            assert interaction.channel
            member_updated = await self.ticket_manager.add_ticket_participants(
                interaction.channel.id, participants_id=[user.id]
            )
            return await interaction.response.send_message(
                content=f"成功將{user.mention}加入此頻道！"
                if member_updated
                else f"{user.mention}已經在此頻道中！",
                ephemeral=True,
            )
        except AssertionError:
            return await interaction.response.send_message(
                content="你不該看到此訊息的...", ephemeral=True
            )
        except ChannelNotTicket:
            return await interaction.response.send_message(
                content="此指令只能在客服頻道中使用。", ephemeral=True
            )

    @app_commands.command(
        name="remove_participant",
        description="將使用者移出客服頻道，需要客服人員身份組才可使用。",
    )
    @app_commands.checks.has_role(cus_service_role_id)
    async def remove_participant(self, interaction: Interaction, user: User):
        try:
            if user.bot:
                return await interaction.response.send_message(
                    content="你不能將機器人從客服頻道中移除。", ephemeral=True
                )
            assert interaction.channel
            member_updated = await self.ticket_manager.remove_ticket_participants(
                interaction.channel.id, participants_id=[user.id]
            )
            return await interaction.response.send_message(
                content=f"成功將{user.mention}移出此頻道！"
                if member_updated
                else f"{user.mention}不在此頻道中！",
                ephemeral=True,
            )
        except AssertionError:
            return await interaction.response.send_message(
                content="你不該看到此訊息的...", ephemeral=True
            )
        except ChannelNotTicket:
            return await interaction.response.send_message(
                content="此指令只能在客服頻道中使用。", ephemeral=True
            )
        except NoParticipants:
            return await interaction.response.send_message(
                content="此客服頻道已經沒有客戶了，你在幹麻？？？", ephemeral=True
            )

    @app_commands.command(name="r", description="回覆指令(只有客服人員能夠使用)")
    @app_commands.checks.has_role(cus_service_role_id)
    async def r(
        self,
        interaction: Interaction,
        reply: app_commands.Transform[ReplyKeys, CannedResponseTransformer(ReplyKeys)],
    ):
        # check if in channel

        if not interaction.channel or not isinstance(interaction.channel, TextChannel):
            # The ticket channel must be a TextChannel because that's how it's coded.
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )

        ticket = await self.ticket_manager.get_ticket(channel_id=interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message(
                "這裡不是客服頻道！", ephemeral=True
            )
        # get customer id & tag stuff
        response_data = CANNED_RESPONSES.get(reply)
        if not response_data:
            return await interaction.response.send_message(
                "錯誤：找不到該回覆訊息。", ephemeral=True
            )
        final_response = response_data.text
        if response_data.mention_user:
            participants = await self.ticket_manager.get_ticket_participants_member(
                ticket_id=ticket.db_id
            )
            if not participants:
                return await interaction.response.send_message(
                    "這個客服頻道沒有客戶，非常詭異", ephemeral=True
                )
            final_response = f"""{", ".join(map(lambda participant: participant.mention, participants))} 
{final_response}"""

        await interaction.channel.send(final_response)

        if reply in {ReplyKeys.CLOSE_PROMPT, ReplyKeys.DONE_PROCESS}:
            await self.ticket_manager.set_ticket_status(
                ticket=ticket, new_status=TicketStatus.RESOLVED
            )
        return await interaction.response.send_message(
            "傳送完成", delete_after=3, ephemeral=True
        )

    @r.error
    async def r_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, MissingRole):
            return await interaction.response.send_message(
                "只有客服人員能夠使用此指令！", ephemeral=True
            )


async def setup(client):
    await client.add_cog(tickets(bot=client, ticket_manager=client.ticket_manager))
