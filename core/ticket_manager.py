from typing import Literal
import discord
from discord.ext import commands
from discord import Guild, User, Member, Embed
from typing import Union
import yaml
from config.models import TicketStatus
from db.database_manager import DatabaseManager
from core.exceptions import ChannelCreationFail
from config.constants import cus_service_role_id, num_to_chinese
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
                for x in business_hours["date_data"]:
                    embed.add_field(
                        name=f"星期{num_to_chinese[x['date'] - 1]}",
                        value=f"{x['start_time']}~{x['end_time']}",
                        inline=False,
                    )
                return embed
        except FileNotFoundError:
            return embed

    async def create_channel(
        self, user: Union[User, Member], guild: Guild, ticket_type: str
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
        # First insert to database
        new_channel = await guild.create_text_channel(
            name=f"{ticket_type}-temp", overwrites=overwrites
        )
        # set next channel name
        msg = await new_channel.send(
            content=f"{user.mention}Hi，有什麼需要服務的嗎~留下訊息後請等待{cus_service_role.mention}回應😊",
            embed=self.get_business_hours_embed(),
        )
        with self.database_manager as db:
            new_channel_name = db.insert(
                table_name="ticket",
                data={
                    "channel_id": new_channel.id,
                    "auto_timeout": 48,
                    "timed_out": 0,
                    "close_msg_id": msg.id,
                    "status": TicketStatus.OPEN,
                },
            )
            await new_channel.edit(name=new_channel_name)

        close_view = None
        await msg.edit()

        return new_channel
