from typing import List, Optional, Union, Dict, Any
from discord.ext import commands
import asyncio
from config.models import Keyword, KeywordType
from db.database_manager import AsyncDatabaseManager


class KeywordManager:
    def __init__(
        self, bot: commands.Bot, database_manager: AsyncDatabaseManager
    ) -> None:
        self.bot = bot
        self.database_manager = database_manager
        self.keywords_table_name = "keywords"
        self.keyword_channel_table_name = "keyword_channel"
        self.keyword_cache = dict()

    async def initialize_cache(self):
        keyword_channel_mapping = await self.database_manager.select(
            table_name=self.keyword_channel_table_name
        )

        keyword_records = await self.database_manager.select(
            table_name=self.keywords_table_name
        )
        if not keyword_records:
            print("No keywords found in database to cache.")
            return
        channels_by_keyword = {}
        for mapping in keyword_channel_mapping:
            word = mapping["keyword"]
            if word not in channels_by_keyword:
                channels_by_keyword[word] = []
            channels_by_keyword[word].append(mapping["channel"])
        assert not isinstance(keyword_records, dict)
        for record in keyword_records:
            kw_id = record["id"]
            trigger = record["trigger"]
            keyword = Keyword(
                id=kw_id,
                trigger=trigger,
                response=record["response"],
                kw_type=record["kw_type"],
                in_ticket_only=record["in_ticket_only"],
                guild_id=record["guild_id"],
                allowed_channel_ids=channels_by_keyword.get(kw_id, []),
            )
            self.keyword_cache[trigger] = keyword

    def get_keyword_by_trigger(self, trigger: str) -> Optional[Keyword]:
        """
        Retrieves a keyword from the cache by its trigger word.
        Returns None if not found.
        Args:
            trigger: The word that triggers the keyword.
        Returns:
            Keyword object or None if not found.
        """
        return self.keyword_cache.get(trigger)

    async def create_keyword(
        self,
        trigger: str,
        response: str,
        kw_type: KeywordType,
        in_ticket_only: bool,
        guild_id: int,
        allowed_channel_ids: Optional[List[int]] = None,
    ) -> Keyword:
        """
        Creates a new keyword in the database and caches it.
        This acts as a factory for Keyword objects.

        Args:
            trigger: The word that triggers the keyword.
            response: The bot's response.
            kw_type: The type of keyword match.
            in_ticket_only: Whether it's restricted to ticket channels.
            guild_id: The guild this keyword belongs to.
            allowed_channel_ids: An optional list of channel IDs where it can trigger.

        Returns:
            The newly created, fully hydrated Keyword object.
        """
        keyword_id = await self.database_manager.insert(
            table_name=self.keywords_table_name,
            data={
                "trigger": trigger,
                "response": response,
                "kw_type": kw_type.value,
                "in_ticket_only": in_ticket_only,
                "guild_id": guild_id,
            },
            returning_col="id",
        )

        final_channel_ids = allowed_channel_ids or []
        if final_channel_ids:
            channel_data = [
                {"keyword_id": keyword_id, "channel_id": cid}
                for cid in final_channel_ids
            ]
            await self.database_manager.insert_many(
                table_name=self.keyword_channel_table_name, data=channel_data
            )

        new_keyword = Keyword(
            id=keyword_id,
            trigger=trigger,
            response=response,
            kw_type=kw_type,
            in_ticket_only=in_ticket_only,
            guild_id=guild_id,
            allowed_channel_ids=final_channel_ids,
        )

        self.keyword_cache[trigger] = new_keyword
        return new_keyword

    async def delete_keyword(self, trigger: str):
        status_cache = self.keyword_cache.pop(
            trigger, None
        )  # Remove from cache if exists
        if not status_cache:
            return False
        rows_affected = await self.database_manager.delete(
            table_name=self.keywords_table_name, criteria={"trigger": trigger}
        )
        return rows_affected > 0

    async def update_keyword(self, trigger: str, data: Dict[str, Any]):
        cached_keyword = self.get_keyword_by_trigger(trigger)
        if not cached_keyword:
            return None
        new_trigger = data.get("trigger")
        if new_trigger and new_trigger != trigger:
            self.keyword_cache.pop(trigger)
            trigger_to_update = new_trigger
        else:
            trigger_to_update = trigger

        await self.database_manager.update(
            table_name=self.keywords_table_name,
            data=data,
            criteria={"id": cached_keyword.id},
        )

        for key, value in data.items():
            if hasattr(cached_keyword, key):
                setattr(cached_keyword, key, value)

        self.keyword_cache[trigger_to_update] = cached_keyword

        return cached_keyword

    async def fetch_keyword(self, id: int) -> Keyword:
        keyword_data = await self.database_manager.select(
            table_name=self.keywords_table_name,
            criteria={"id": id},
            fetch_one=True,
        )
        if not keyword_data:
            raise
        assert isinstance(keyword_data, dict)
        return Keyword(
            id=keyword_data["id"],
            trigger=keyword_data["trigger"],
            response=keyword_data["response"],
            kw_type=keyword_data["kw_type"],
            in_ticket_only=keyword_data["in_ticket_only"],
            guild_id=keyword_data["guild_id"],
        )

    async def get_keyword(self, id: int) -> Union[Keyword, None]:
        """
        This function uses keyword cache first, and uses fetch_keyword if cache miss.
        """
        keyword = self.keyword_cache.get(id)
        if not keyword:
            try:
                keyword = await self.fetch_keyword(id)
                if not keyword:
                    return None
                # Update the cache with the fetched keyword
                self.keyword_cache[id] = keyword
                return keyword
            except Exception as e:
                print(f"Error fetching keyword with id {id}: {e}")
                return None
