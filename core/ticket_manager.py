import io
import discord
from discord.ext import commands
from discord import Guild, User, Member, Embed, TextChannel, Client
from typing import Union, List, Optional
from discord.ui import View
import yaml
from config.models import (
    CloseMessageType,
    Ticket,
    TicketStatus,
    TicketType,
)
from db.database_manager import DatabaseManager
from core.exceptions import ChannelCreationFail, ChannelNotTicket, TicketNotFound
from config.constants import (
    cus_service_role_id,
    eng_to_chinese,
    bot_token,
    THEME_COLOR,
    archive_channel_id,
)
import asyncio
from utils.embed_utils import create_themed_embed
import subprocess
from datetime import datetime, timedelta

import tempfile
import pathlib

from view.feedback_views import FeedBackSystem, feedbackEmbed


class TicketManager:
    def __init__(self, bot: commands.Bot, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.bot = bot
        self.ticket_table_name = "tickets"
        self.ticket_panels_table_name = "ticket_panels"
        self.ticket_participants_table_name = "ticket_participants"

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

    def is_ticket_channel(self, channel_id: int) -> bool:
        with self.database_manager as db:
            return (
                True
                if db.select(
                    table_name=self.ticket_table_name,
                    criteria={"channel_id": channel_id},
                    fetch_one=True,
                )
                else False
            )

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

        with self.database_manager as db:
            ticket_data = db.select(
                table_name="tickets",
                criteria=provided_criteria,
                fetch_one=True,
            )
            if not ticket_data:
                return None
            assert isinstance(ticket_data, dict)
            return Ticket(
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

    def get_ticket_participants(self, ticket_id: int) -> Union[List[int], None]:
        with self.database_manager as db:
            participants = db.select(
                table_name=self.ticket_participants_table_name,
                criteria={"ticket_id": ticket_id},
            )
            if not participants:
                return None
            assert isinstance(participants, list)
            return [p["participant_id"] for p in participants]

    async def get_ticket_participants_member(
        self, ticket_id: int
    ) -> Union[List[Member], None]:
        participants_ids = self.get_ticket_participants(ticket_id=ticket_id)
        if not participants_ids:
            return None
        ticket_cnl = await self.get_ticket(ticket_id=ticket_id)
        if not ticket_cnl:
            return None
        cnl = self.bot.get_channel(ticket_cnl.channel_id)
        if not cnl:
            return None
        assert isinstance(cnl, TextChannel)
        members = []
        for part_id in participants_ids:
            member = cnl.guild.get_member(part_id)
            if not member:
                continue
            members.append(member)
        return members

    async def add_ticket_participant(
        self, channel_id: int, participant_id: int
    ) -> Union[List[int], None]:
        ticket = await self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket
        ticket_guild = self.bot.get_guild(ticket.guild_id)
        if not ticket_guild:
            ticket_guild = await self.bot.fetch_guild(ticket.guild_id)
        ticket_channel = ticket_guild.get_channel(channel_id)
        assert isinstance(ticket_channel, TextChannel)
        member_obj = ticket_guild.get_member(participant_id)

        if not member_obj:
            raise Exception(f"Member object cannot be find with id {participant_id}")

        if not isinstance(ticket_channel, TextChannel):
            raise Exception(
                f"Ticket channel with channel id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )

        overwrites = ticket_channel.overwrites
        overwrites[member_obj] = discord.PermissionOverwrite(read_messages=True)
        with self.database_manager as db:
            try:
                db.insert(
                    table_name=self.ticket_participants_table_name,
                    data={"ticket_id": ticket.db_id, "participant_id": participant_id},
                    returning_col="ticket_id",
                )
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
            member = channel.guild.get_member(part_id)
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

        ticket_guild = self.bot.get_guild(ticket.guild_id)
        # This uses the cache

        if not ticket_guild:
            ticket_guild = await self.bot.fetch_guild(ticket.guild_id)

        ticket_channel = ticket_guild.get_channel(channel_id)
        if not isinstance(ticket_channel, TextChannel):
            raise Exception(
                f"Ticket channel with channel id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )
        current_participants = self.get_ticket_participants(ticket_id=ticket.db_id)
        current_participants = (
            set(current_participants) if current_participants else set()
        )
        member_to_add_to_db = await self._update_participants_permissions(
            channel=ticket_channel,
            participants_id=participants_id,
            allow_read=True,
            current_participants=current_participants,
        )
        with self.database_manager as db:
            data = [
                {
                    "ticket_id": ticket.db_id,
                    "participant_id": participant_id,
                }
                for participant_id in member_to_add_to_db
            ]
            db.insert_many(
                table_name=self.ticket_participants_table_name,
                data=data,
            )
        return member_to_add_to_db

    async def remove_ticket_participants(
        self, channel_id: int, participants_id: List[int]
    ) -> Union[List[int], None]:
        ticket = await self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket

        ticket_guild = self.bot.get_guild(ticket.guild_id)
        # This uses the cache

        if not ticket_guild:
            ticket_guild = await self.bot.fetch_guild(ticket.guild_id)

        ticket_channel = ticket_guild.get_channel(channel_id)
        if not isinstance(ticket_channel, TextChannel):
            raise Exception(
                f"Ticket channel with channel id {channel_id} cannot be found in the guild with id {ticket.guild_id}."
            )
        current_participants = self.get_ticket_participants(ticket_id=ticket.db_id)
        if not current_participants:
            raise Exception("No participants found for the ticket.")
        current_participants = set(current_participants)
        member_to_remove_from_db = await self._update_participants_permissions(
            channel=ticket_channel,
            participants_id=participants_id,
            allow_read=False,
            current_participants=current_participants,
        )

        with self.database_manager as db:
            db.delete(
                table_name=self.ticket_participants_table_name,
                criteria={
                    "ticket_id": ticket.db_id,
                    "participant_id": member_to_remove_from_db,
                },
            )
        return member_to_remove_from_db

    async def get_close_msg_id(self, channel_id: int) -> Union[int, None]:
        """Get the close message ID for a given channel ID."""
        with self.database_manager as db:
            result = db.select(
                table_name=self.ticket_table_name,
                criteria={"channel_id": channel_id},
                fetch_one=True,
            )
            try:
                assert result, "No ticket found for the given channel ID."
                assert isinstance(result, dict)
                return result["close_msg_id"]
            except (AssertionError, KeyError):
                print(
                    f"Error retrieving close message ID for channel {channel_id}: {result}"
                )
                return None

    async def set_close_msg(
        self, channel_id: int, close_msg_id: int, close_msg_type: CloseMessageType
    ):
        """Set the close message id and type for a given channel ID."""
        with self.database_manager as db:
            db.update(
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
        with self.database_manager as db:
            new_ticket_id = db.insert(
                table_name=self.ticket_table_name,
                data={
                    "channel_id": new_channel.id,
                    "auto_timeout": 48,
                    "timed_out": 0,
                    "close_msg_id": msg.id,
                    "status": TicketStatus.OPEN,
                    "ticket_type": TicketType(ticket_type),
                    "guild_id": guild.id,
                    "close_msg_type": CloseMessageType.CLOSE_TOGGLE,
                },
            )
            # We just set it manually since creating a Ticket object here is meaningless.
            await new_channel.edit(
                name=f"{ticket_type}-{new_ticket_id:04d}-{TicketStatus.OPEN.string_repr}"
            )
            db.insert(
                table_name=self.ticket_participants_table_name,
                data={"ticket_id": new_ticket_id, "participant_id": user.id},
                returning_col="ticket_id",
            )

        return new_channel

    def _run_archive_exporter_sync(self, channel_id: int, temp_dir: str) -> str:
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
        await self.set_ticket_status(
            ticket=ticket, new_status=TicketStatus.CLOSED, ticket_channel=channel
        )

        def _sync_update_and_select():
            with self.database_manager as db:
                db.update(
                    table_name=self.ticket_table_name,
                    data={"status": TicketStatus.CLOSED},
                    criteria={"channel_id": channel.id},
                )
                # We can also fetch the participants in the same transaction
                return db.select(
                    "ticket_participants", criteria={"ticket_id": ticket.db_id}
                )

        loop = asyncio.get_running_loop()
        participants_id = await loop.run_in_executor(None, _sync_update_and_select)
        customers_mention = ""
        customers: List[Union[User, Member]] = []
        assert participants_id and isinstance(participants_id, list)
        cus_num = 0
        for participant_id in participants_id:
            part_id = participant_id["participant_id"]
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
            with tempfile.TemporaryDirectory() as temp_dir:
                transcript_path_str = await loop.run_in_executor(
                    None, self._run_archive_exporter_sync, channel.id, temp_dir
                )

                transcript_path = pathlib.Path(transcript_path_str)
                transcript_bytes = transcript_path.read_bytes()
                filename = transcript_path.name

            archive_channel = self.bot.get_channel(archive_channel_id)
            assert isinstance(archive_channel, TextChannel)

            UTC_to_GMT = timedelta(hours=8)
            new = channel.created_at + UTC_to_GMT
            created_time_str = new.strftime("%Y/%m/%d %H:%M:%S")
            closed_time_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

            archive_embed = discord.Embed(
                title=f"頻道 「{channel.name}」紀錄",
                description=f"顧客：{customers_mention}\n此頻道開啟於{created_time_str}\n顧客數量{cus_num}\n關閉於{closed_time_str}",
                color=THEME_COLOR,
            )

            transcript_file = discord.File(
                fp=io.BytesIO(transcript_bytes),
                filename=f"{filename}.html",
            )
            new = await archive_channel.send(embed=archive_embed)
            new = await new.edit(attachments=[transcript_file])

            msg = await msg.edit(content="生成完成✅傳送回饋單給客戶中...")
            view = FeedBackSystem()
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
        with self.database_manager as db:
            db.delete(
                table_name=self.ticket_table_name, criteria={"channel_id": channel.id}
            )
            await channel.delete()

    async def reopen_ticket(self, channel: TextChannel):
        ticket = await self.get_ticket(channel_id=channel.id)
        if not ticket:
            raise ChannelNotTicket
        await self.set_ticket_status(
            ticket=ticket, new_status=TicketStatus.OPEN, ticket_channel=channel
        )
        participants_id = self.get_ticket_participants(ticket_id=ticket.db_id)
        assert participants_id
        await self._update_participants_permissions(
            channel=channel,
            participants_id=participants_id,
            allow_read=True,
            current_participants=set(),
        )

    async def set_ticket_status(
        self,
        ticket: Ticket,
        new_status: TicketStatus,
        guild: Optional[Guild] = None,
        ticket_channel: Optional[TextChannel] = None,
    ):
        if ticket.status == new_status:
            return
        ticket.status = new_status
        with self.database_manager as db:
            db.update(
                table_name=self.ticket_table_name,
                data={"status": new_status.value},
                criteria={"id": ticket.db_id},
            )
        await self.set_ticket_channel_name(
            ticket=ticket, guild=guild, ticket_channel=ticket_channel
        )

    async def set_ticket_channel_name(
        self,
        ticket: Ticket,
        guild: Optional[Guild] = None,
        ticket_channel: Optional[TextChannel] = None,
    ):
        """
        This fucntion sets the ticket's channel name with format : {ticket.ticket_type.value}-{ticket.db_id:04d}-{status_name if status_name else '未知'}, where status_name = ticket_status_name_chinese.get(ticket.status).
        Args:
            ticket (Ticket): The ticket to be changed.
            guild (Optional[Guild]): The guild that the ticket is in.
            ticket_channel (Optional[TextChannel]): The textchannel object of the ticket.

        Notes:
            If guild or ticket_channel has a mismatch with the provided ticket infomation, we will try fix that.

        Raises:
            discord.errors.NotFound, if the channel or the guild (the latter is unlikely) was deleted.
        Returns:
            None, if everything works fine.
        """
        if not ticket_channel or ticket_channel.id != ticket.channel_id:
            # This means a mismatch or ticket_channel is not given, so we have to get it ourselves.
            # We do the computation if guild is not given or the guild is given but is mismatched
            if not guild or (guild and guild.id != ticket.guild_id):
                guild = self.bot.get_guild(ticket.guild_id)
                if not guild:
                    guild = await self.bot.fetch_guild(ticket.guild_id)

            ticket_cnl_temp = guild.get_channel(ticket.channel_id)
            if not ticket_channel:
                ticket_cnl_temp = await guild.fetch_channel(ticket.channel_id)
            assert isinstance(ticket_cnl_temp, TextChannel)
            ticket_channel = ticket_cnl_temp

        # We pray for cache hit everytime.
        status_name = ticket.status.string_repr
        await ticket_channel.edit(
            name=f"{ticket.ticket_type.value}-{ticket.db_id:04d}-{status_name if status_name else '未知'}"
        )
