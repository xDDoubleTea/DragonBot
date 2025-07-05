import discord
from discord.ext import commands
from discord import Guild, User, Member, Embed, TextChannel
from typing import Union, List
from discord.ui import View
import yaml
from config.models import CloseMessageType, Ticket, TicketStatus
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


class TicketManager:
    def __init__(self, bot: commands.Bot, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.bot = bot

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
                    table_name="tickets",
                    criteria={"channel_id": channel_id},
                    fetch_one=True,
                )
                else False
            )

    async def get_ticket(self, channel_id: int) -> Union[Ticket, None]:
        with self.database_manager as db:
            ticket = db.select(
                table_name="tickets",
                criteria={"channel_id": channel_id},
                fetch_one=True,
            )
            if not ticket:
                return None
            assert isinstance(ticket, dict)
            return Ticket(
                db_id=ticket["id"],
                channel_id=channel_id,
                auto_timeout=ticket["auto_timeout"],
                timed_out=ticket["timed_out"],
                close_msg_id=ticket["close_msg_id"],
                status=TicketStatus(ticket["status"]),
                guild_id=ticket["guild_id"],
                close_msg_type=ticket["close_msg_type"],
            )

    def get_ticket_participants(self, ticket_id: int) -> Union[List[int], None]:
        with self.database_manager as db:
            participants = db.select(
                table_name="ticket_participants",
                criteria={"ticket_id": ticket_id},
            )
            if not participants:
                return None
            assert isinstance(participants, list)
            return [p["participant_id"] for p in participants]

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
                    table_name="ticket_participants",
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
                table_name="ticket_participants",
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
                table_name="ticket_participants",
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
                table_name="tickets",
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
                table_name="tickets",
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
                table_name="tickets",
                data={
                    "channel_id": new_channel.id,
                    "auto_timeout": 48,
                    "timed_out": 0,
                    "close_msg_id": msg.id,
                    "status": TicketStatus.OPEN,
                    "guild_id": guild.id,
                    "close_msg_type": CloseMessageType.CLOSE_TOGGLE,
                },
            )
            await new_channel.edit(name=f"{ticket_type}-{new_ticket_id}")
            db.insert(
                table_name="ticket_participants",
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

    async def close_ticket(self, channel: TextChannel):
        ticket = await self.get_ticket(channel_id=channel.id)
        if not ticket:
            raise TicketNotFound

        def _sync_update_and_select():
            with self.database_manager as db:
                db.update(
                    table_name="tickets",
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
        assert participants_id and isinstance(participants_id, list)
        cus_num = 0
        for participant_id in participants_id:
            part_id = participant_id["participant_id"]
            member = channel.guild.get_member(part_id)
            if member:
                await channel.set_permissions(target=member, read_messages=False)
                customers_mention += member.mention + ", "
                cus_num += 1
            else:
                print(
                    f"Warning: Could not find member with ID {part_id} in guild with id {ticket.guild_id}."
                )
            # Generate the channel history archive
        customers_mention = customers_mention.rstrip(", ")
        msg = await channel.send("頻道紀錄檔案生成中...")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                transcript_path = await loop.run_in_executor(
                    None, self._run_archive_exporter_sync, channel.id, temp_dir
                )

                transcript_file = discord.File(
                    fp=transcript_path,
                    filename=f"{channel.name}.html",
                )

                archive_channel = self.bot.get_channel(archive_channel_id)
                assert isinstance(archive_channel, TextChannel)
                UTC_to_GMT = timedelta(hours=8)
                new = channel.created_at + UTC_to_GMT
                created_time_str = new.strftime("%Y/%m/%d %H:%M:%S")
                closed_time_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                embed = discord.Embed(
                    title=f"頻道 「{channel.name}」紀錄",
                    description=f"顧客：{customers_mention}\n此頻道開啟於{created_time_str}\n顧客數量{cus_num}\n關閉於{closed_time_str}",
                    color=THEME_COLOR,
                )
                new = await archive_channel.send(embed=embed)
                new = await new.edit(attachments=[transcript_file])

            msg = await msg.edit(content="生成完成✅傳送回饋單給客戶中...")
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
            db.delete(table_name="tickets", criteria={"channel_id": channel.id})
            await channel.delete()

    async def reopen_ticket(self, channel: TextChannel):
        ticket = await self.get_ticket(channel_id=channel.id)
        if not ticket:
            raise ChannelNotTicket
        participants_id = self.get_ticket_participants(ticket_id=ticket.db_id)
        assert participants_id
        await self._update_participants_permissions(
            channel=channel,
            participants_id=participants_id,
            allow_read=True,
            current_participants=set(),
        )
