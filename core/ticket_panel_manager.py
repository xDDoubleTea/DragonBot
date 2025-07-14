from typing import List, Dict
from asyncpg import NoDataFoundError, UniqueViolationError
from discord import Client, Guild, TextChannel
from discord.ext.commands import Bot
from discord.message import Message, PartialMessage
from db.database_manager import AsyncDatabaseManager
from config.models import PanelMessageData
from utils.discord_utils import (
    try_get_message,
    try_get_guild,
    try_get_channel,
)


class PanelNotFound(Exception):
    pass


class TicketPanelManager:
    def __init__(self, bot: Client | Bot, database_manager: AsyncDatabaseManager):
        self.bot = bot
        self.database_manager = database_manager
        self.ticket_panels_table_name = "ticket_panels"
        self.ticket_panels: Dict[int, PanelMessageData] = dict()

    async def _try_get_guild(self, guild_id: int) -> Guild | None:
        return await try_get_guild(bot=self.bot, guild_id=guild_id)

    async def _try_get_panel(
        self, panel_message_data: PanelMessageData
    ) -> tuple[Guild, TextChannel, Message | PartialMessage] | None:
        """
        This function tries to get a tuple (guild, channel, message) of the given panel_message_data,
        if any of the values in the tuple is None, we return None.
        """
        guild = await self._try_get_guild(guild_id=panel_message_data.guild_id)
        if not guild:
            return None
        channel = await try_get_channel(
            guild=guild, channel_id=panel_message_data.channel_id
        )
        if not channel or not isinstance(channel, TextChannel):
            return None
        message = await try_get_message(
            channel=channel, message_id=panel_message_data.message_id
        )
        if not message:
            return None
        return (guild, channel, message)

    async def get_panel(
        self, *, guild_id: int | None, channel_id: int | None, message_id: int | None
    ) -> PanelMessageData | None:
        """
        This function returns the corresponding PanelMessageData dataclass if all of the given arguments meets exactly one record in cache or in database.
        Returns None if not. (Think of it as SQL query.)
        Almost always provide guild_id to this function.
        """
        # First check cache
        if guild_id and guild_id in self.ticket_panels.keys():
            cached_panel = self.ticket_panels[guild_id]
            if (channel_id and cached_panel.channel_id == channel_id) and (
                message_id and cached_panel.message_id == message_id
            ):
                return cached_panel
        else:
            for panel in self.ticket_panels.values():
                if (channel_id and panel.channel_id == channel_id) and (
                    message_id and panel.message_id == message_id
                ):
                    # Found a match on other criteria
                    return panel
        # Then check database
        criteria = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_id": message_id,
        }
        provided_criteria = {k: v for k, v in criteria.items() if v}
        if not provided_criteria:
            return None
        db_query = await self.database_manager.select(
            table_name=self.ticket_panels_table_name,
            criteria=provided_criteria,
            fetch_one=True,
        )
        if not db_query:
            return None
        assert db_query
        panel_data = PanelMessageData(
            guild_id=db_query["guild_id"],
            channel_id=db_query["channel_id"],
            message_id=db_query["message_id"],
        )
        self.ticket_panels[panel_data.guild_id] = panel_data
        return panel_data

    async def load_ticket_panel_messages(self) -> List[Message]:
        """
        Load all ticket panels from the database and store them in the ticket_panels dictionary.
        (Initializes the cache.)
        """
        all_panels = await self.database_manager.select(
            table_name=self.ticket_panels_table_name
        )
        print("Restoring ticket panels....")
        if not all_panels:
            print("No ticket panels found in the database. Skipping restoration.")
            return []
        assert isinstance(all_panels, list)
        restore_message = []
        for panel in all_panels:
            guild_id = panel.get("guild_id")
            channel_id = panel.get("channel_id")
            message_id = panel.get("message_id")
            assert guild_id and channel_id and message_id
            try:
                print(f"Restoring panel for guild with ID {guild_id}")
                get_panel_data = await self._try_get_panel(
                    panel_message_data=PanelMessageData(
                        guild_id=guild_id, channel_id=channel_id, message_id=message_id
                    )
                )
                if not get_panel_data:
                    print(
                        f"Cannot find panel with (guild_id, channel_id, message_id) == ({guild_id}, {channel_id}, {message_id}). Skipping..."
                    )
                    await self.database_manager.delete(
                        table_name=self.ticket_panels_table_name,
                        criteria={"guild_id": guild_id},
                    )
                    continue
                _, _, message = get_panel_data
                restore_message.append(message)
                self.ticket_panels[guild_id] = PanelMessageData(
                    guild_id=guild_id, channel_id=channel_id, message_id=message_id
                )

            except Exception as e:
                print(
                    f"An error occurred while re-attaching view for guild {guild_id}: {e}"
                )
        return restore_message

    async def insert_or_update_panel(self, panel_message_data: PanelMessageData):
        self.ticket_panels[panel_message_data.guild_id] = panel_message_data
        try:
            await self.database_manager.insert(
                table_name=self.ticket_panels_table_name,
                data={
                    "guild_id": panel_message_data.guild_id,
                    "channel_id": panel_message_data.channel_id,
                    "message_id": panel_message_data.message_id,
                },
                returning_col="guild_id",
            )
        except UniqueViolationError:
            await self.database_manager.update(
                table_name=self.ticket_panels_table_name,
                data={"guild_id": panel_message_data.guild_id},
            )

    async def update_panel(self, new_panel_message_data: PanelMessageData):
        self.ticket_panels[new_panel_message_data.guild_id] = new_panel_message_data
        await self.database_manager.update(
            table_name=self.ticket_panels_table_name,
            data={"guild_id": new_panel_message_data.guild_id},
        )

    async def delete_panel(self, panel_message_data: PanelMessageData):
        self.ticket_panels.pop(panel_message_data.guild_id, None)
        try:
            await self.database_manager.delete(
                table_name=self.ticket_panels_table_name,
                criteria={"guild_id": panel_message_data.guild_id},
            )
        except NoDataFoundError:
            pass
        except Exception as e:
            print(e)

    async def delete_panel_by_guild_id(self, guild_id: int):
        self.ticket_panels.pop(guild_id, None)
        try:
            await self.database_manager.delete(
                table_name=self.ticket_panels_table_name,
                criteria={"guild_id": guild_id},
            )
        except NoDataFoundError:
            pass
        except Exception as e:
            print(e)
