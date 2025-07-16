from bs4.element import Tag
from discord import Client
from typing import Any, Dict, List
from config.models import CurrencyIndex, CurrencyTransformation
from db.database_manager import AsyncDatabaseManager
from discord.ext.commands import Bot
from config import currency_information_url
import requests
import bs4
from intervals import IntervalDict
import intervals


class TransformationNotSpecified(Exception):
    def __init__(
        self, message: str = "Currency transformation is not specified for this guild."
    ):
        self.message = message
        super().__init__()


class ValueNotCovered(ValueError):
    """
    This is raised when the given value of amount is not covered by any interval in the transformation.
    """

    def __init__(
        self,
        message: str = "The amount given is not covered by any interval in the transformation.",
    ):
        self.message = message
        super().__init__()


class CurrencyManager:
    def __init__(
        self, bot: Bot | Client, database_manager: AsyncDatabaseManager
    ) -> None:
        self.bot = bot
        self.database_manager = database_manager
        self.guild_transformation_cache: Dict[int, CurrencyTransformation] = dict()
        self.cur_transformation_table_name = "currency_transformation"

    @staticmethod
    async def get_currency(cur: CurrencyIndex) -> float | None:
        url = currency_information_url
        req = requests.get(url)
        soup = bs4.BeautifulSoup(req.text, "html.parser")

        tbody = soup.find("tbody")
        if not isinstance(tbody, Tag):
            return None
        all_rate = tbody.find_all("tr")

        cur_type = "即期"
        if not all_rate or len(all_rate) <= cur.index:
            return None
        row = all_rate[cur.index]
        if not isinstance(row, Tag):
            return None
        rate_element = row.select_one(
            f'td[data-table="本行{cur_type}賣出"].print_width'
        )
        if rate_element and rate_element.string:
            # The .string attribute can also be None if the tag is empty
            rate_str = rate_element.string.strip()
            try:
                return float(rate_str)
            except (ValueError, TypeError):
                return None

        return None

    @staticmethod
    async def to_currency_transformation(
        raw_data: List[Any],
    ) -> CurrencyTransformation | None:
        if not raw_data:
            return None
        cur_transformation = CurrencyTransformation(
            guild_id=raw_data[0]["guild_id"],
            taxes_info=IntervalDict(
                {
                    intervals.closedopen(
                        lower=data["lower_bound"], upper=data["upper_bound"]
                    ): data["tax"]
                    for data in raw_data
                }
            ),
        )
        return cur_transformation

    async def get_guild_transformation(
        self, guild_id: int
    ) -> CurrencyTransformation | None:
        """
        This function gets all transformation information per guild.
        """
        pass
        if transformation := self.guild_transformation_cache.get(guild_id, None):
            print(
                f"Cache hit for guild currency transformation for guild ID {guild_id}."
            )
            return transformation
        # Cache miss
        transformation_info = await self.database_manager.select(
            table_name=self.cur_transformation_table_name,
            criteria={"guild_id": guild_id},
        )
        if not transformation_info:
            return None
        assert isinstance(transformation_info, list)
        cur_transformation = await self.to_currency_transformation(
            raw_data=transformation_info
        )
        if not cur_transformation:
            return None
        # Lazy loading (Fancy name for cache on read)
        self.guild_transformation_cache[cur_transformation.guild_id] = (
            cur_transformation
        )
        return cur_transformation

    async def set_guild_transformation_interval_tax(
        self,
        guild_id: int,
        lower_bound: float | None,
        upper_bound: float | None,
        tax: int,
    ):
        lower_bound = lower_bound if lower_bound else 0
        upper_bound = upper_bound if upper_bound else float("inf")
        await self.database_manager.insert(
            table_name=self.cur_transformation_table_name,
            data={
                "guild_id": guild_id,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "tax": tax,
            },
            returning_col="id",
        )
        new_interval = intervals.closedopen(
            lower=lower_bound,
            upper=upper_bound,
        )
        if cur_transformation := self.guild_transformation_cache.get(guild_id):
            cur_transformation.taxes_info[new_interval] = tax
            return
        self.guild_transformation_cache[guild_id] = CurrencyTransformation(
            guild_id=guild_id, taxes_info=IntervalDict({new_interval: tax})
        )

    async def currency_transformer(
        self, guild_id: int, amount: float, cur_index: CurrencyIndex
    ) -> float:
        transformation = await self.get_guild_transformation(guild_id=guild_id)
        if not transformation:
            raise TransformationNotSpecified
        tax = transformation.taxes_info.get(amount)
        if not tax:
            raise ValueNotCovered
        new_amount = await self.get_currency(cur=cur_index)
        if not new_amount:
            # This should not happen.
            raise
        return new_amount + tax
