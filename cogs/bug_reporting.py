from typing import Optional
from discord import Attachment, Client, Interaction, app_commands
from discord.ext.commands import Bot, Cog

from core.bug_reporter import BugReporter
from main import DragonBot


class BugReport(Cog):
    def __init__(self, bot: Client | Bot, bug_reporter: BugReporter):
        self.bot = bot
        self.bug_reporter = bug_reporter

    @app_commands.command(name="bug_report", description="Reports a bug to developer.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        bug_title="The title of the bug.",
        bug_description="The description of the bug, please be accurate on how does the bug behave.",
        bug_reproduce="How to reproduce the bug. Please provide detailed explanation.",
        bug_reproduce_demo="A screenshot or (better) a video, gif, etc... to show us how to reproduce the bug and the behaviour of it.",
    )
    async def bug_report(
        self,
        interaction: Interaction,
        bug_title: str,
        bug_description: str,
        bug_reproduce: str,
        bug_reproduce_demo: Optional[Attachment],
    ):
        if bug_reproduce_demo:
            await interaction.response.send_message(
                file=await bug_reproduce_demo.to_file()
            )


async def setup(client: DragonBot):
    await client.add_cog(BugReport(bot=client, bug_reporter=client.bug_reporter))
