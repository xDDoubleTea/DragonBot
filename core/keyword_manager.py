from typing import List, Optional, Union, Dict, Any
from discord.ext import commands
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
        self.keyword_cache: Dict[str, Keyword] = dict()

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
            word_id = mapping["keyword_id"]
            if word_id not in channels_by_keyword:
                channels_by_keyword[word_id] = []
            channels_by_keyword[word_id].append(mapping["channel_id"])
        assert not isinstance(keyword_records, dict)
        for record in keyword_records:
            kw_id = record["id"]
            trigger = record["trigger"]
            keyword = Keyword(
                id=kw_id,
                trigger=trigger,
                response=record["response"],
                kw_type=KeywordType(record["kw_type"]),
                in_ticket_only=record["in_ticket_only"],
                guild_id=record["guild_id"],
                mention_participants=record["mention_participants"],
                allowed_channel_ids=channels_by_keyword.get(kw_id, []),
            )
            self.keyword_cache[trigger] = keyword

    def get_all_keywords(self) -> Dict[str, Keyword]:
        return self.keyword_cache

    def get_keyword_by_trigger(self, trigger: str, guild_id: int) -> Optional[Keyword]:
        """
        Retrieves a keyword from the cache by its trigger word.
        Returns None if not found.
        Args:
            trigger: The word that triggers the keyword.
        Returns:
            Keyword object or None if not found.
        """
        kw = self.keyword_cache.get(trigger)
        if not kw:
            return None
        return kw if kw.guild_id == guild_id else None

    def get_all_keywords_in_guild(self, guild_id: int):
        return {
            key: word
            for key, word in self.keyword_cache.items()
            if word.guild_id == guild_id
        }

    async def create_keyword(
        self,
        trigger: str,
        response: str,
        kw_type: KeywordType,
        in_ticket_only: bool,
        guild_id: int,
        allowed_channel_ids: Optional[List[int]] = None,
        mention_participants: bool = False,
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
                "mention_participants": mention_participants,
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
            mention_participants=mention_participants,
            allowed_channel_ids=final_channel_ids,
        )

        self.keyword_cache[trigger] = new_keyword
        return new_keyword

    async def delete_keyword(self, trigger: str, guild_id: int):
        kw = self.keyword_cache.get(trigger, None)
        if not kw:
            return False
        if kw.guild_id == guild_id:
            self.keyword_cache.pop(trigger, None)
        # Remove from cache if exists and guild id matches
        rows_affected = await self.database_manager.delete(
            table_name=self.keywords_table_name,
            criteria={"trigger": trigger, "guild_id": guild_id},
        )
        return rows_affected > 0

    async def update_keyword(self, trigger: str, data: Dict[str, Any], guild_id: int):
        cached_keyword = self.get_keyword_by_trigger(trigger, guild_id=guild_id)
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

    async def append_keyword_channels(
        self, trigger: str, channel_ids: List[int], guild_id: int
    ):
        """
        Appends the allowed channels for a keyword.
        Args:
            trigger: The keyword trigger to update.
            channel_ids: List of channel IDs to allow for this keyword.
            guild_id: The guild this keyword belongs to.
        """
        keyword = self.get_keyword_by_trigger(trigger, guild_id=guild_id)
        if not keyword:
            return None
        channel_data = [
            {"keyword_id": keyword.id, "channel_id": cid}
            for cid in channel_ids
            if cid not in keyword.allowed_channel_ids
        ]
        await self.database_manager.insert_many(
            table_name=self.keyword_channel_table_name, data=channel_data
        )
        # Update the cache
        keyword.allowed_channel_ids += channel_ids
        self.keyword_cache[trigger] = keyword
        return keyword

    async def get_keyword_channels(self, trigger: str, guild_id: int) -> List[int]:
        """
        Retrieves the allowed channels for a keyword.
        Args:
            trigger: The keyword trigger to fetch channels for.
            guild_id: The guild this keyword belongs to.
        Returns:
            List of channel IDs where this keyword is allowed.
        """
        keyword = self.get_keyword_by_trigger(trigger, guild_id=guild_id)
        if not keyword:
            return []
        return keyword.allowed_channel_ids

    async def remove_keyword_channels(
        self, trigger: str, channel_ids: List[int], guild_id: int
    ):
        """
        Removes the allowed channels for a keyword.
        Args:
            trigger: The keyword trigger to update.
            channel_ids: List of channel IDs to remove from allowed channels.
            guild_id: The guild this keyword belongs to.
        """
        keyword = self.get_keyword_by_trigger(trigger, guild_id=guild_id)
        if not keyword:
            return None
        await self.database_manager.delete(
            table_name=self.keyword_channel_table_name,
            criteria={"keyword_id": keyword.id, "channel_id": channel_ids},
        )
        # Update the cache
        keyword.allowed_channel_ids = [
            cid for cid in keyword.allowed_channel_ids if cid not in channel_ids
        ]
        self.keyword_cache[trigger] = keyword
        return keyword

    async def fetch_keyword(self, trigger: str) -> Keyword:
        keyword_data = await self.database_manager.select(
            table_name=self.keywords_table_name,
            criteria={"trigger": trigger},
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
            mention_participants=keyword_data["mention_participants"],
        )

    async def get_keyword(self, trigger: str) -> Union[Keyword, None]:
        """
        This function uses keyword cache first, and uses fetch_keyword if cache miss.
        """
        keyword = self.keyword_cache.get(trigger)
        if not keyword:
            try:
                keyword = await self.fetch_keyword(trigger)
                if not keyword:
                    return None
                # Update the cache with the fetched keyword
                self.keyword_cache[trigger] = keyword
                return keyword
            except Exception as e:
                print(f"Error fetching keyword with {trigger}: {e}")
                return None
