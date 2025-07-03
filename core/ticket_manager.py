import discord
from discord.ext import commands
from discord import Guild, User, Member, Embed, TextChannel
from typing import Union, List
from discord.ui import View
import yaml
from config.models import Ticket, TicketStatus
from db.database_manager import DatabaseManager
from core.exceptions import ChannelCreationFail, ChannelNotTicket
from config.constants import cus_service_role_id, eng_to_chinese
from utils.embed_utils import create_themed_embed


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

    def get_ticket(self, channel_id: int) -> Union[Ticket, None]:
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

    def add_ticket_participants(
        self, channel_id: int, participant_id: int
    ) -> Union[List[int], None]:
        ticket = self.get_ticket(channel_id=channel_id)
        if not ticket:
            raise ChannelNotTicket
        with self.database_manager as db:
            db.insert(
                table_name="ticket_participants",
                data={"ticket_id": ticket.db_id, "participant_id": participant_id},
                returning_col="ticket_id",
            )

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

    async def set_close_msg_id(self, channel_id: int, close_msg_id: int):
        """Set the close message ID for a given channel ID."""
        with self.database_manager as db:
            db.update(
                table_name="tickets",
                data={"close_msg_id": close_msg_id},
                criteria={"channel_id": channel_id},
            )

    async def create_channel(
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
                },
            )
            await new_channel.edit(name=f"{ticket_type}-{new_ticket_id}")
            db.insert(
                table_name="ticket_participants",
                data={"ticket_id": new_ticket_id, "participant_id": user.id},
                returning_col="ticket_id",
            )

        return new_channel

    async def close_channel(self, channel: TextChannel):
        with self.database_manager as db:
            db.update(
                table_name="tickets",
                data={"status": TicketStatus.CLOSED},
                criteria={"channel_id": channel.id},
            )
            ticket = db.select(
                table_name="tickets",
                criteria={"channel_id": channel.id},
                fetch_one=True,
            )
            assert ticket and isinstance(ticket, dict)
            # Set the participants' permission
            participants_id = db.select(
                "ticket_participants", criteria={"ticket_id": ticket["id"]}
            )
            print(participants_id)
            assert participants_id and isinstance(participants_id, list)
            for participant_id in participants_id:
                part_id = participant_id["participant_id"]
                member = channel.guild.get_member(part_id)
                if member:
                    await channel.set_permissions(target=member, read_messages=False)
