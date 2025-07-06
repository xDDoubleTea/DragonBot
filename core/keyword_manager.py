from typing import Union, Dict, Any, List
from discord.ext import commands
import asyncpg
from config.models import Keyword
from db.database_manager import DatabaseManager


class KeywordManager:
    def __init__(self, bot: commands.Bot, database_manager: DatabaseManager) -> None:
        self.bot = bot
        self.database_manager = database_manager
        self.keywords_table_name = "keywords"
        self.keyword_cache = dict()
        self.keyword_cache = self._fetch_all_keywords_from_db()

    def _fetch_all_keywords_from_db(self):
        with self.database_manager as db:
            keyword_data_all = db.select(
                table_name=self.keywords_table_name,
            )
            if not keyword_data_all:
                return dict()
            assert not isinstance(keyword_data_all, dict)
            return {
                keyword_data["word"]: Keyword(
                    word=keyword_data["word"],
                    response=keyword_data["response"],
                    kw_type=keyword_data["kw_type"],
                    in_ticket_only=keyword_data["in_ticket_only"],
                )
                for keyword_data in keyword_data_all
            }

    def insert_keyword(self, keyword: Keyword) -> str:
        self.keyword_cache[keyword.word] = keyword
        with self.database_manager as db:
            return db.insert(
                table_name=self.keywords_table_name,
                data={
                    "word": keyword.word,
                    "response": keyword.response,
                    "kw_type": keyword.kw_type,
                    "in_ticket_only": keyword.in_ticket_only,
                },
                returning_col="word",
            )

    def delete_keyword(self, word: str):
        with self.database_manager as db:
            db.delete(table_name=self.keywords_table_name, criteria={"word": word})
        self.keyword_cache.pop(word, None)  # Remove from cache if exists

    def update_keyword(self, word: str, data: Dict[str, Any]):
        with self.database_manager as db:
            db.update(
                table_name=self.keywords_table_name, data=data, criteria={"word": word}
            )
        # Update the cache
        # How?

    async def fetch_keyword(self, word: str) -> Keyword:
        with self.database_manager as db:
            keyword_data = db.select(
                table_name=self.keywords_table_name,
                criteria={"word": word},
                fetch_one=True,
            )
            if not keyword_data:
                raise
            assert isinstance(keyword_data, dict)
            return Keyword(
                word=word,
                response=keyword_data["response"],
                kw_type=keyword_data["kw_type"],
                in_ticket_only=keyword_data["in_ticket_only"],
            )

    def get_keyword(self, word: str) -> Union[Keyword, None]:
        """
        This function uses keyword cache first, and uses fetch_keyword if no cache hit.
        """
        return self.keyword_cache.get(word)
