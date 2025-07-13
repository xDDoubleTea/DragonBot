from discord import app_commands, Interaction
from typing import Optional
from discord.ext.commands import Cog

from core.feedback_manager import FeedbackManager
from main import DragonBot


class general(Cog):
    feeback_stat = app_commands.Group(
        name="feeback_stat",
        description="Feedback statistics.",
    )

    def __init__(self, bot: DragonBot, feedback_manager: FeedbackManager):
        self.bot = bot
        self.feedback_manager = feedback_manager

    @feeback_stat.command(
        name="check_feedback_leaderboard", description="回傳回饋單填寫排行榜"
    )
    @app_commands.describe(
        limit="排行榜紀錄筆數，上限為10，若填入超過10則自動設為10，預設為5"
    )
    @app_commands.guild_only()
    async def check_feedback_leaderboard(
        self, interaction: Interaction, limit: int = 5
    ):
        assert interaction.guild and interaction.guild_id
        await interaction.response.defer(thinking=True)
        if limit <= 0:
            return await interaction.followup.send("欲查詢排行榜之紀錄筆數需為正整數")
        leaderboard = await self.feedback_manager.get_feedback_leaderboard(
            guild_id=interaction.guild_id, limit=limit
        )
        if not leaderboard:
            return await interaction.followup.send("此伺服器沒有回饋單填寫紀錄...")
        leaderboard_embed = await self.feedback_manager.to_feedback_leaderboard_embed(
            leaderboard=leaderboard, guild=interaction.guild
        )
        assert leaderboard_embed
        await interaction.followup.send(embed=leaderboard_embed)


async def setup(client: DragonBot):
    await client.add_cog(general(bot=client, feedback_manager=client.feedback_manager))
