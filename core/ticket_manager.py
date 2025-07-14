import io
import discord
from discord import Guild, User, Member, Embed, TextChannel, Client
from discord.abc import GuildChannel
from typing import Union, List, Optional, Dict, Set
from discord.ext.commands import Bot
from discord.ext.commands.errors import ChannelNotFound
from discord.ui import View
import yaml
from config.models import (
    CloseMessageType,
    Ticket,
    TicketStatus,
    TicketType,
    PanelMessageData,
)
from core.feedback_manager import FeedbackManager
from db.database_manager import AsyncDatabaseManager
from core.exceptions import ChannelCreationFail, ChannelNotTicket, TicketNotFound
from config.constants import (
    cus_service_role_id,
    eng_to_chinese,
    bot_token,
    THEME_COLOR,
    archive_channel_id,
)

import asyncio
from utils.discord_utils import (
    get_or_fetch,
    try_get_channel_by_bot,
    try_get_channel,
    try_get_guild,
    try_get_member,
)
from utils.embed_utils import create_themed_embed
import subprocess
from datetime import datetime, timedelta

import tempfile
import pathlib

from view.feedback_views import FeedBackSystem, feedbackEmbed


class TicketManager:
    def __init__(
        self,
        bot: Bot | Client,
        database_manager: AsyncDatabaseManager,
        feedback_manager: FeedbackManager,
    ):
        self.database_manager = database_manager
        self.bot = bot
        self.ticket_table_name = "tickets"
        self.feedback_manager = feedback_manager
        self.ticket_panels_table_name = "ticket_panels"
        self.ticket_participants_table_name = "ticket_participants"
        self.panel_messages: Dict[int, PanelMessageData] = dict()
        self.ticket_caches: Dict[int, Ticket] = dict()

    async def _try_get_channel_by_bot(
        self, channel_id: int
    ) -> Optional[Union[GuildChannel, discord.Thread]]:
        """
        Attempts to get a channel by ID from the guild, falling back to fetching it if not found.
        """
        return await try_get_channel_by_bot(bot=self.bot, channel_id=channel_id)

    async def try_get_ticket_in_cache_by_channel_id(
        self, channel_id: int
    ) -> Optional[Ticket]:
        """
        Attempts to get a ticket by channel ID from the cache.
        """
        for ticket in self.ticket_caches.values():
            if ticket.channel_id == channel_id:
                return ticket
        return None

    async def _try_get_guild(self, guild_id: int) -> Optional[Guild]:
        return await try_get_guild(bot=self.bot, guild_id=guild_id)

    def get_business_hours_embed(self) -> Embed:
        embed = create_themed_embed(
            title="Date", description="檢查在線時間", client=self.bot
        )
        try:
            with open("config.yaml", "r") as file:
                config = yaml.safe_load(file)
                business_hours = config.get("business_hours", [])
                # print(business_hours)
                for x in business_hours:
                    embed.add_field(
                        name=f"星期{eng_to_chinese[x['day']]}",
                        value=f"{x['start_time']}~{x['end_time']}",
                        inline=False,
                    )
                return embed
        except FileNotFoundError:
            return embed

    async def init_cache(self):
        """
        Initialize the cache for ticket panels and tickets.
        This function should be called when the bot starts.
        """
        # Load ticket panels into cache
        print("Loading ticket panels into cache...")
        ticket_panels = await self.database_manager.select(
            table_name=self.ticket_panels_table_name
        )
        for panel in ticket_panels:
            self.panel_messages[panel["guild_id"]] = PanelMessageData(
                message_id=panel["message_id"],
                channel_id=panel["channel_id"],
                guild_id=panel["guild_id"],
            )
        print("Ticket panels loaded into cache.")
        print("Loading tickets into cache...")
        # Load tickets into cache
        tickets = await self.database_manager.select(table_name=self.ticket_table_name)
        for ticket_data in tickets:
            ticket = Ticket(
                db_id=ticket_data["id"],
                channel_id=ticket_data["channel_id"],
                auto_timeout=ticket_data["auto_timeout"],
                timed_out=ticket_data["timed_out"],
                close_msg_id=ticket_data["close_msg_id"],
                status=TicketStatus.from_id(ticket_data["status"]),
                ticket_type=TicketType(ticket_data["ticket_type"]),
                guild_id=ticket_data["guild_id"],
                close_msg_type=CloseMessageType(ticket_data["close_msg_type"]),
                participants=set(),
            )
            participants = await self.get_ticket_participants_id(ticket_id=ticket.db_id)
            ticket.participants = set(participants) if participants else set()

            self.ticket_caches[ticket.db_id] = ticket
        print("Tickets loaded into cache.")

    async def is_ticket_channel(self, channel_id: int) -> bool:
        return True if await self.get_ticket(channel_id=channel_id) else False

    async def get_ticket(
        self, *, ticket_id: Optional[int] = None, channel_id: Optional[int] = None
    ) -> Union[Ticket, None]:
        criteria = {
            "id": ticket_id,
            "channel_id": channel_id,
        }
        provided_criteria = {k: v for k, v in criteria.items() if v is not None}

        if len(provided_criteria) != 1:
            raise ValueError(
                "This function must be called with exactly one keyword argument."
            )

        if ticket_id and (ticket := self.ticket_caches.get(ticket_id, None)):
            return ticket
        if channel_id:
            for ticket in self.ticket_caches.values():
                if ticket.channel_id == channel_id:
                    return ticket
        # No cache hit. Select from database.
        ticket_data = await self.database_manager.select(
            table_name="tickets",
            criteria=provided_criteria,
            fetch_one=True,
        )
        if not ticket_data:
            return None
        ticket = Ticket(
            db_id=ticket_data["id"],
            channel_id=ticket_data["channel_id"],
            auto_timeout=ticket_data["auto_timeout"],
            timed_out=ticket_data["timed_out"],
            close_msg_id=ticket_data["close_msg_id"],
            status=TicketStatus.from_id(ticket_data["status"]),
            ticket_type=TicketType(ticket_data["ticket_type"]),
            guild_id=ticket_data["guild_id"],
            close_msg_type=ticket_data["close_msg_type"],
        )
        # Cache on read
        self.ticket_caches[ticket.db_id] = ticket
        return ticket

    async def get_ticket_participants_id(self, ticket_id: int) -> Set[int]:
        if ticket := self.ticket_caches.get(ticket_id):
            return ticket.participants
        participants = await self.database_manager.select(
            table_name=self.ticket_participants_table_name,
            criteria={"ticket_id": ticket_id},
        )
        if not participants:
            return set()
        assert isinstance(participants, list)
        participants_set = {p["participant_id"] for p in participants}
        return participants_set

    async def archive_ticket(self, channel_id: int) -> tuple[bytes, str]:
        """
        Archive the ticket with the given ticket_id.
        This function will return a bytes object which can be loaded with discord.File and the name of the exported file.
        Raises: ChannelNotTicket if ticket is not found, ChannelNotFound if the channelid cannot be found in the guild.
        """
        ticket = await self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket(f"Channel with ID {channel_id} is not a ticket.")
        channel = await self._try_get_channel_by_bot(channel_id=channel_id)
        if not channel:
            raise ChannelNotFound(
                f"Channel with ID {ticket.channel_id} not found in the guild."
            )
        assert isinstance(channel, TextChannel)
        transcript_bytes: bytes
        with tempfile.TemporaryDirectory() as temp_dir:
            transcript_path_str = await self._run_archive_exporter_sync(
                channel.id, temp_dir
            )
            transcript_path = pathlib.Path(transcript_path_str)
            transcript_bytes = transcript_path.read_bytes()
            filename = transcript_path.name

        return transcript_bytes, filename

    async def get_ticket_participants_member(
        self, ticket_id: int
    ) -> Union[Set[Member], None]:
        participants_ids = await self.get_ticket_participants_id(ticket_id=ticket_id)
        if not participants_ids:
            return None
        ticket = await self.get_ticket(ticket_id=ticket_id)
        if not ticket:
            return None
        guild = await self._try_get_guild(guild_id=ticket.guild_id)
        if not guild:
            return None
        members = set()
        for part_id in participants_ids:
            member = await get_or_fetch(
                container=guild,
                obj_id=part_id,
                get_method_name="get_member",
                fetch_method_name="fetch_member",
            )
            if not member:
                continue
            members.add(member)
        return members

    async def add_ticket_participant(
        self, channel_id: int, participant_id: int
    ) -> Union[List[int], None]:
        ticket = await self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket
        ticket_guild = await self._try_get_guild(guild_id=ticket.guild_id)
        if not ticket_guild:
            raise Exception(
                f"Guild with id {ticket.guild_id} cannot be found. Please check if the bot is in the guild."
            )
        ticket_channel = await try_get_channel(
            guild=ticket_guild, channel_id=ticket.channel_id
        )
        if not ticket_channel:
            raise Exception(
                f"Channel with id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )

        member_obj = await try_get_member(guild=ticket_guild, member_id=participant_id)
        if not member_obj:
            raise Exception(f"Member object cannot be find with id {participant_id}")

        if not isinstance(ticket_channel, TextChannel):
            raise Exception(
                f"Ticket channel with channel id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )

        overwrites = ticket_channel.overwrites
        overwrites[member_obj] = discord.PermissionOverwrite(read_messages=True)
        try:
            await self.database_manager.insert(
                table_name=self.ticket_participants_table_name,
                data={"ticket_id": ticket.db_id, "participant_id": participant_id},
                returning_col="ticket_id",
            )
            self.ticket_caches[ticket.db_id].participants.add(participant_id)
        except Exception as e:
            print(
                f"Error occured when adding user with id {participant_id} into database. {e}"
            )

    async def _update_participants_permissions(
        self,
        channel: TextChannel,
        participants_id: List[int],
        allow_read: bool,
        current_participants: set,
    ) -> List[int]:
        """
        A private helper to grant or revoke channel visibility for a list of participants.

        Args:
            channel: The ticket channel to modify.
            participants_id: A list of member IDs.
            allow_read: If True, grants read access. If False, revokes it.
            current_participants: A set of currently active participants in the channel.
        """
        permission_updates = []
        member_updates = []
        for part_id in participants_id:
            member = await try_get_member(guild=channel.guild, member_id=part_id)
            if not member:
                print(
                    f"Warning: Could not find member with ID {part_id} in guild {channel.guild.id} to update permissions."
                )
                continue
            if allow_read and part_id not in current_participants:
                # If we are granting read access and the member is not already a participant
                member_updates.append(part_id)
            elif not allow_read and part_id in current_participants:
                # If we are revoking read access and the member is already a participant
                member_updates.append(part_id)

            overwrite = discord.PermissionOverwrite(
                view_channel=allow_read,
                read_messages=allow_read,
                send_messages=allow_read,
            )
            permission_updates.append(
                channel.set_permissions(member, overwrite=overwrite)
            )

        # Run all permission updates concurrently for better performance
        if permission_updates:
            await asyncio.gather(*permission_updates)

        return member_updates

    async def add_ticket_participants(
        self, channel_id: int, participants_id: List[int]
    ) -> Union[List[int], None]:
        ticket = await self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket

        ticket_guild = await self._try_get_guild(guild_id=ticket.guild_id)

        if not ticket_guild:
            raise Exception(
                "Guild cannot be found. Please check if the bot is in the guild."
            )

        ticket_channel = await try_get_channel(
            guild=ticket_guild, channel_id=channel_id
        )
        if not isinstance(ticket_channel, TextChannel):
            raise Exception(
                f"Ticket channel with channel id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )
        current_participants = await self.get_ticket_participants_id(
            ticket_id=ticket.db_id
        )
        current_participants = (
            set(current_participants) if current_participants else set()
        )
        member_to_add_to_db = await self._update_participants_permissions(
            channel=ticket_channel,
            participants_id=participants_id,
            allow_read=True,
            current_participants=current_participants,
        )
        data = [
            {
                "ticket_id": ticket.db_id,
                "participant_id": participant_id,
            }
            for participant_id in member_to_add_to_db
        ]
        await self.database_manager.insert_many(
            table_name=self.ticket_participants_table_name,
            data=data,
        )
        self.ticket_caches[ticket.db_id].participants = self.ticket_caches[
            ticket.db_id
        ].participants.union(member_to_add_to_db)
        return member_to_add_to_db

    async def remove_ticket_participants(
        self, channel_id: int, participants_id: List[int]
    ) -> Union[List[int], None]:
        ticket = await self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket

        ticket_guild = await self._try_get_guild(guild_id=ticket.guild_id)

        if not ticket_guild:
            raise Exception(
                "Guild cannot be found. Please check if the bot is in the guild."
            )

        ticket_channel = await try_get_channel(
            guild=ticket_guild, channel_id=channel_id
        )
        if not isinstance(ticket_channel, TextChannel):
            raise Exception(
                f"Ticket channel with channel id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )
        current_participants = await self.get_ticket_participants_id(
            ticket_id=ticket.db_id
        )
        if not current_participants:
            raise Exception("No participants found for the ticket.")
        current_participants = set(current_participants)
        member_to_remove_from_db = await self._update_participants_permissions(
            channel=ticket_channel,
            participants_id=participants_id,
            allow_read=False,
            current_participants=current_participants,
        )

        await self.database_manager.delete(
            table_name=self.ticket_participants_table_name,
            criteria={
                "ticket_id": ticket.db_id,
                "participant_id": member_to_remove_from_db,
            },
        )
        self.ticket_caches[ticket.db_id].participants.difference_update(
            member_to_remove_from_db
        )
        return member_to_remove_from_db

    async def get_close_msg_id(self, channel_id: int) -> Union[int, None]:
        """Get the close message ID for a given channel ID."""
        for ticket in self.ticket_caches.values():
            if ticket.channel_id == channel_id:
                return ticket.close_msg_id
        result = await self.database_manager.select(
            table_name=self.ticket_table_name,
            criteria={"channel_id": channel_id},
            fetch_one=True,
        )
        try:
            assert result, "No ticket found for the given channel ID."
            assert isinstance(result, dict)
            self.ticket_caches[result["id"]] = Ticket(
                db_id=result["id"],
                channel_id=channel_id,
                auto_timeout=result["auto_timeout"],
                timed_out=result["timed_out"],
                close_msg_id=result["close_msg_id"],
                status=result["status"],
                ticket_type=result["ticket_type"],
                guild_id=result["guild_id"],
                close_msg_type=result["close_msg_id"],
                participants=await self.get_ticket_participants_id(
                    ticket_id=result["id"]
                ),
            )
            return result["close_msg_id"]
        except (AssertionError, KeyError):
            print(
                f"Error retrieving close message ID for channel {channel_id}: {result}"
            )
            return None

    async def set_close_msg_id(
        self, channel_id: int, close_msg_id: int, close_msg_type: CloseMessageType
    ):
        """This function should only be called after validating the channel is a ticket.
        Set the close message id and type for a given channel ID."""
        ticket = await self.get_ticket(channel_id=channel_id)
        assert ticket
        ticket.close_msg_id = close_msg_id
        ticket.close_msg_type = close_msg_type
        self.ticket_caches[ticket.db_id] = ticket
        await self.database_manager.update(
            table_name=self.ticket_table_name,
            data={"close_msg_id": close_msg_id, "close_msg_type": close_msg_type},
            criteria={"channel_id": channel_id},
        )

    async def create_ticket(
        self,
        user: Union[User, Member],
        guild: Guild,
        ticket_type: str,
        close_view: View,
    ) -> Union[discord.TextChannel, None]:
        if isinstance(user, User) and not isinstance(user, Member):
            user_temp = guild.get_member(user.id)
            if not user_temp:
                raise ChannelCreationFail("User is not in guild.")
            user = user_temp
        cus_service_role = guild.get_role(cus_service_role_id)
        assert cus_service_role
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True),
            cus_service_role: discord.PermissionOverwrite(read_messages=True),
        }
        # create new ticket
        # First create with a temporary name
        new_channel = await guild.create_text_channel(
            name=f"{ticket_type}-temp", overwrites=overwrites
        )
        # set next channel name
        msg = await new_channel.send(
            content=f"{user.mention}Hi，有什麼需要服務的嗎~留下訊息後請等待{cus_service_role.mention}回應😊",
            embed=self.get_business_hours_embed(),
            view=close_view,
        )
        new_ticket_id = await self.database_manager.insert(
            table_name=self.ticket_table_name,
            data={
                "channel_id": new_channel.id,
                "auto_timeout": 48,
                "timed_out": 0,
                "close_msg_id": msg.id,
                "status": TicketStatus.OPEN.id,
                "ticket_type": TicketType(ticket_type),
                "guild_id": guild.id,
                "close_msg_type": CloseMessageType.CLOSE_TOGGLE,
            },
            returning_col="id",
        )
        self.ticket_caches[new_ticket_id] = Ticket(
            db_id=new_ticket_id,
            channel_id=new_channel.id,
            auto_timeout=48,
            timed_out=0,
            close_msg_id=msg.id,
            status=TicketStatus.OPEN,
            ticket_type=TicketType(ticket_type),
            guild_id=guild.id,
            close_msg_type=CloseMessageType.CLOSE_TOGGLE,
        )
        # We just set it manually since creating a Ticket object here is meaningless.
        await new_channel.edit(
            name=f"{ticket_type}-{new_ticket_id:04d}-{TicketStatus.OPEN.string_repr}"
        )
        await self.database_manager.insert(
            table_name=self.ticket_participants_table_name,
            data={"ticket_id": new_ticket_id, "participant_id": user.id},
            returning_col="ticket_id",
        )
        self.ticket_caches[new_ticket_id].participants.add(user.id)

        return new_channel

    async def _run_archive_exporter_sync(self, channel_id: int, temp_dir: str) -> str:
        """
        A synchronous, blocking function that runs the chat exporter.
        This is designed to be run in an executor.
        It returns the path to the exported file.
        """
        output_path = pathlib.Path(temp_dir)
        assert bot_token

        command = [
            "vendor/DiscordChatExporterCLI/DiscordChatExporter.Cli",
            "export",
            "--channel",
            str(channel_id),
            "--token",
            bot_token,
            "--output",
            str(output_path),
        ]

        # This is the blocking call
        subprocess.run(command, capture_output=True, text=True, check=True)

        exported_files = list(output_path.glob("*.html"))
        if not exported_files:
            raise FileNotFoundError(
                "Chat export completed, but no HTML file was found."
            )

        # Return the full path to the transcript
        return str(exported_files[0])

    async def close_ticket(self, channel: TextChannel, client: Client):
        ticket = await self.get_ticket(channel_id=channel.id)
        if not ticket:
            raise TicketNotFound
        await self.set_ticket_status(ticket=ticket, new_status=TicketStatus.CLOSED)

        async def _sync_update_and_select():
            self.ticket_caches[ticket.db_id].status = TicketStatus.CLOSED
            await self.database_manager.update(
                table_name=self.ticket_table_name,
                data={"status": TicketStatus.CLOSED.id},
                criteria={"id": ticket.db_id},
            )
            # We can also fetch the participants in the same transaction
            return await self.get_ticket_participants_id(ticket_id=ticket.db_id)

        participants_id = await _sync_update_and_select()
        customers_mention = ""
        customers: List[Union[User, Member]] = []
        assert participants_id and isinstance(participants_id, set)
        cus_num = 0
        for part_id in participants_id:
            member = channel.guild.get_member(part_id)
            if member:
                await channel.set_permissions(target=member, read_messages=False)
                customers_mention += member.mention + ", "
                customers.append(member)
                cus_num += 1
            else:
                print(
                    f"Warning: Could not find member with ID {part_id} in guild with id {ticket.guild_id}."
                )
            # Generate the channel history archive
        customers_mention = customers_mention.rstrip(", ")
        msg = await channel.send("頻道紀錄檔案生成中...")
        try:
            transcript_bytes: bytes
            transcript_bytes, filename = await self.archive_ticket(
                channel_id=channel.id
            )

            archive_channel = await self._try_get_channel_by_bot(
                channel_id=archive_channel_id
            )
            if not archive_channel:
                raise ChannelNotTicket(
                    f"Archive channel with ID {archive_channel_id} not found."
                )
            assert isinstance(archive_channel, TextChannel)
            transcript_file = discord.File(
                fp=io.BytesIO(transcript_bytes),
                filename=f"{filename}",
            )

            UTC_to_GMT = timedelta(hours=8)
            new = channel.created_at + UTC_to_GMT
            created_time_str = new.strftime("%Y/%m/%d %H:%M:%S")
            closed_time_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

            archive_embed = discord.Embed(
                title=f"頻道 「{channel.name}」紀錄",
                description=f"顧客：{customers_mention}\n此頻道開啟於{created_time_str}\n顧客數量{cus_num}\n關閉於{closed_time_str}",
                color=THEME_COLOR,
            )

            new = await archive_channel.send(embed=archive_embed, file=transcript_file)

            msg = await msg.edit(content="生成完成✅傳送回饋單給客戶中...")
            view = FeedBackSystem(
                ticket_id=ticket.db_id,
                guild_id=ticket.guild_id,
                feedback_manager=self.feedback_manager,
            )
            feedback_embed = feedbackEmbed(channel=channel, client=client)
            for customer in customers:
                if customer:
                    try:
                        customer_transcript_file = discord.File(
                            io.BytesIO(transcript_bytes), filename=filename
                        )
                        await customer.send(
                            content="此為對話記錄檔案：",
                            embed=archive_embed,
                            file=customer_transcript_file,
                        )
                        await customer.send(
                            content="說明：點選星數來代表今天服務的滿意度，而下拉式選單可選擇評語(若誤按或未使用服務請不用評價)",
                            embed=feedback_embed,
                            view=view,
                        )
                    except discord.errors.Forbidden:
                        print(
                            f"User {customer.name} does not allow private messages, skipping..."
                        )
                    except Exception as e:
                        print(f"Error: {e}")
        except subprocess.CalledProcessError as e:
            # This block will run if the exporter command fails
            print(f"Error exporting channel {channel.id}: {e}")
            await msg.edit(content="錯誤：生成頻道紀錄時發生問題，請檢查後台日誌。")
            raise Exception("錯誤：生成頻道紀錄時發生問題，請檢查後台日誌。")
        except FileNotFoundError:
            # This block will run if the DiscordChatExporter.Cli executable is not found
            print("Error: DiscordChatExporter.Cli not found.")
            await msg.edit(content="錯誤：找不到匯出工具。")
            raise FileNotFoundError("Error: DiscordChatExporter.Cli not found.")

    async def delete_ticket(self, channel: TextChannel):
        ticket = await self.get_ticket(channel_id=channel.id)
        if not ticket:
            raise ChannelNotTicket
        # Delete the ticket from the cache
        if ticket.db_id in self.ticket_caches.keys():
            del self.ticket_caches[ticket.db_id]
        await self.database_manager.delete(
            table_name=self.ticket_table_name, criteria={"id": ticket.db_id}
        )
        await channel.delete()

    async def reopen_ticket(self, channel: TextChannel):
        ticket = await self.get_ticket(channel_id=channel.id)
        if not ticket:
            raise ChannelNotTicket
        await self.set_ticket_status(ticket=ticket, new_status=TicketStatus.OPEN)
        participants_id = await self.get_ticket_participants_id(ticket_id=ticket.db_id)
        assert participants_id
        await self._update_participants_permissions(
            channel=channel,
            participants_id=list(participants_id),
            allow_read=True,
            current_participants=set(),
        )

    async def set_ticket_status(
        self,
        ticket: Ticket,
        new_status: TicketStatus,
    ) -> None:
        """
        This function sets the ticket's status to new_status.
        Args:
            ticket (Ticket): The ticket to be changed.
            new_status (TicketStatus): The new status to be set.
            guild (Optional[Guild]): The guild that the ticket is in.
            ticket_channel (Optional[TextChannel]): The textchannel object of the ticket.
        Raises:
            discord.errors.NotFound, if the channel or the guild (the latter is unlikely) was deleted.
            TicketNotFound, if the channel with the ticket's channel_id was not found in the guild.
        Returns:
            None, if everything works fine.
        """
        if ticket.status == new_status:
            return
        ticket.status = new_status
        await self.database_manager.update(
            table_name=self.ticket_table_name,
            data={"status": new_status.id},
            criteria={"id": ticket.db_id},
        )
        self.ticket_caches[ticket.db_id] = ticket
        try:
            await self.set_ticket_channel_name(ticket=ticket)
        except TicketNotFound as e:
            print(
                f"Error: {e}. The channel with the ticket's channel_id was not found in the guild."
            )
            # We delete the record in the cache since the ticket should likely have been deleted
            self.ticket_caches.pop(ticket.db_id)
            raise e

    async def set_ticket_channel_name(
        self,
        ticket: Ticket,
    ) -> None:
        """
        This fucntion sets the ticket's channel name with format : {ticket.ticket_type.value}-{ticket.db_id:04d}-{status_name if status_name else '未知'}, where status_name = ticket_status_name_chinese.get(ticket.status).
        Args:
            ticket (Ticket): The ticket to be changed.

        Raises:
            TicketNotFound, if the channel with the ticket's channel_id was not found in the guild.
        Returns:
            None, if everything works fine.
        """
        ticket_guild = await try_get_guild(bot=self.bot, guild_id=ticket.guild_id)
        if not ticket_guild:
            raise TicketNotFound(
                f"Ticket channel with ID {ticket.channel_id} not found in the guild with ID {ticket.guild_id}."
            )
        ticket_channel = await try_get_channel(
            guild=ticket_guild, channel_id=ticket.channel_id
        )
        if not ticket_channel:
            raise TicketNotFound(
                f"Ticket channel with ID {ticket.channel_id} not found in the guild with ID {ticket.guild_id}."
            )
        assert isinstance(ticket_channel, TextChannel)
        status_name = ticket.status.string_repr
        try:
            # Just to be really safe.
            await ticket_channel.edit(
                name=f"{ticket.ticket_type.value}-{ticket.db_id:04d}-{status_name if status_name else '未知'}"
            )
        except (discord.errors.HTTPException, discord.errors.NotFound):
            raise TicketNotFound(
                f"Ticket channel with ID {ticket.channel_id} not found in the guild with ID {ticket.guild_id}."
            )
