from typing import Dict, List
import asyncpg
from discord import Client, Embed, Guild
from discord.ext.commands import Bot
from core.exceptions import DBNotInit
from db.database_manager import AsyncDatabaseManager
from config.models import FeedbackEntry, FeedbackLeaderboardEntry, FeedbackStats
from utils.embed_utils import add_std_footer, create_themed_embed
from utils.discord_utils import try_get_member


class NotEnoughFeedbacks(Exception):
    pass


class FeedbackManager:
    def __init__(self, bot: Bot | Client, database_manager: AsyncDatabaseManager):
        self.bot = bot
        self.database_manager = database_manager
        self.feedbacks_table_name = "feedbacks"
        self.average_rating_cache: Dict[int, float] = dict()
        self.total_ratings_cache: Dict[int, int] = dict()

    # async def init_caches(self):
    #     distinct_guild_counts = 0
    #     if not self.database_manager._pool:
    #         raise DBNotInit
    #     async with self.database_manager._pool.acquire() as conn:
    #         sql_query = (
    #             " SELECT COUNT(DISTINCT guild_id) AS unique_guild_count FROM feedback;"
    #         )
    #         stats_row: asyncpg.Record | None = await conn.fetchrow(sql_query)
    #         if stats_row:
    #             distinct_guild_counts = stats_row["unique_guild_count"]
    #     if not distinct_guild_counts:
    #         return

    async def insert_feedback_entry(self, feedback_entry: FeedbackEntry):
        try:
            await self.database_manager.insert(
                table_name=self.feedbacks_table_name,
                data={
                    "customer_id": feedback_entry.customer_id,
                    "guild_id": feedback_entry.guild_id,
                    "rating": feedback_entry.rating,
                    "ticket_id": feedback_entry.ticket_id,
                },
                returning_col="ticket_id",
            )
            if self.total_ratings_cache.get(feedback_entry.guild_id):
                self.total_ratings_cache[feedback_entry.guild_id] += 1
            else:
                self.total_ratings_cache[feedback_entry.guild_id] = 1
            if self.average_rating_cache.get(feedback_entry.guild_id):
                self.average_rating_cache[feedback_entry.guild_id] = (
                    self.average_rating_cache[feedback_entry.guild_id]
                    + feedback_entry.rating
                ) / self.total_ratings_cache[feedback_entry.guild_id]
            else:
                self.average_rating_cache[feedback_entry.guild_id] = (
                    feedback_entry.rating
                )
        except asyncpg.UniqueViolationError:
            # The ticket was reopened, in this case we don't count.
            pass

    async def update_feedback_message(
        self, ticket_id: int, guild_id: int, customer_id: int, feedback_message: str
    ):
        await self.database_manager.update(
            table_name=self.feedbacks_table_name,
            data={"feedback_message": feedback_message},
            criteria={
                "ticket_id": ticket_id,
                "guild_id": guild_id,
                "customer_id": customer_id,
            },
        )

    async def get_avg_rating(self, guild_id: int) -> float | None:
        sql_query = (
            "SELECT AVG(rating) AS average_rating FROM feedbacks WHERE guild_id = $1"
        )
        if not self.database_manager._pool:
            raise DBNotInit
        async with self.database_manager._pool.acquire() as conn:
            stats_row: asyncpg.Record | None = await conn.fetchrow(sql_query, guild_id)
        if not stats_row:
            return None
        self.average_rating_cache[guild_id] = stats_row["average_rating"]
        return float(stats_row["average_rating"])

    async def get_feedback_rating(self, guild_id: int) -> FeedbackStats | None:
        """
        Fetches and calculates feedback statistics for a specific guild.

        Args:
            guild_id: The ID of the guild to fetch statistics for.

        Returns:
            A FeedbackStats object or None if no feedback exists for that guild.
        """
        sql_query = """
        SELECT
            AVG(rating) AS average_rating,
            COUNT(*) AS total_ratings,
            COUNT(*) FILTER (WHERE rating = 5) AS five_star_ratings,
            COUNT(*) FILTER (WHERE rating = 4) AS four_star_ratings,
            COUNT(*) FILTER (WHERE rating = 3) AS three_star_ratings,
            COUNT(*) FILTER (WHERE rating = 2) AS two_star_ratings,
            COUNT(*) FILTER (WHERE rating = 1) AS one_star_ratings
        FROM
        feedbacks
        WHERE guild_id = $1;
        """
        if not self.database_manager._pool:
            raise DBNotInit
        async with self.database_manager._pool.acquire() as conn:
            stats_row: asyncpg.Record | None = await conn.fetchrow(sql_query, guild_id)
        if not stats_row or stats_row["total_ratings"] == 0:
            return None
        self.average_rating_cache[guild_id] = float(stats_row["average_rating"])
        self.total_ratings_cache[guild_id] = int(stats_row["total_ratings"])
        return FeedbackStats(
            average_rating=float(stats_row["average_rating"]),
            total_ratings=stats_row["total_ratings"],
            five_star_ratings=stats_row["five_star_ratings"],
            four_star_ratings=stats_row["four_star_ratings"],
            three_star_ratings=stats_row["three_star_ratings"],
            two_star_ratings=stats_row["two_star_ratings"],
            one_star_ratings=stats_row["one_star_ratings"],
        )

    async def to_feedback_leaderboard_embed(
        self, leaderboard: List[FeedbackLeaderboardEntry], guild: Guild
    ) -> Embed | None:
        if not leaderboard:
            raise NotEnoughFeedbacks
        embed = create_themed_embed(
            title="回饋單填寫排行榜",
            description=f"{guild.name}的排行榜\n此功能為鼓勵填寫回饋單而製作",
            client=self.bot,
        )
        add_std_footer(embed=embed, client=self.bot)
        for entry in leaderboard:
            display_name = entry.customer_id
            member = await try_get_member(guild=guild, member_id=entry.customer_id)
            if member:
                display_name = member.display_name
            field_value = f"回饋單填寫次數：{entry.feedback_count}\n平均評價：{round(entry.average_rating, 1)}"
            embed.add_field(
                name=f"顧客：{display_name}", value=field_value, inline=False
            )
        return embed

    async def get_feedback_leaderboard(
        self, guild_id: int, limit: int = 5
    ) -> List[FeedbackLeaderboardEntry] | None:
        sql_query = """
            SELECT
                customer_id,
                COUNT(*) AS feedback_count,
                AVG(rating) AS average_rating
            FROM
                feedbacks
            WHERE
                guild_id = $1
            GROUP BY
                customer_id
            ORDER BY
                feedback_count DESC, average_rating DESC
            LIMIT $2;
            """
        if not self.database_manager._pool:
            raise DBNotInit
        async with self.database_manager._pool.acquire() as conn:
            assert isinstance(conn, asyncpg.connection.Connection)
            rows: List[asyncpg.Record] = await conn.fetch(
                sql_query,
                guild_id,
                limit,
            )
        if not rows:
            return None

        return [
            FeedbackLeaderboardEntry(
                customer_id=row["customer_id"],
                feedback_count=row["feedback_count"],
                average_rating=row["average_rating"],
            )
            for row in rows
        ]
