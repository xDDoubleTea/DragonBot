import os
import discord
from discord.ext import commands
from config import (
    pre,
    app_id,
    bot_token,
    My_user_id,
    version,
    app_mode,
    db_url,
    MY_GUILD,
)
from core.ticket_manager import TicketManager
from core.keyword_manager import KeywordManager
from db.database_manager import DatabaseManager


class DragonBot(commands.Bot):
    def __init__(self):
        assert pre is not None, "Prefix must be defined in the config"
        super().__init__(
            command_prefix=pre,
            intents=discord.Intents.all(),
            help_command=None,
            description=f"Dragon Bot version {version}\n Mode {app_mode}",
            application_id=app_id,
        )
        assert db_url is not None
        self.db_manager = DatabaseManager(database_url=db_url)
        self.ticket_manager = TicketManager(bot=self, database_manager=self.db_manager)
        self.keyword_manager = KeywordManager(
            bot=self, database_manager=self.db_manager
        )

    async def on_ready(self):
        print(f"{self.user} is now online!")
        await self.change_presence(
            activity=discord.Game(f"Developed by {self.get_user(My_user_id)}")
        )
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def setup_hook(self):
        for cog in filter(
            lambda file: file.endswith(".py"),
            os.listdir("./cogs"),
        ):
            await self.load_extension(f"cogs.{cog[:-3]}")


def main():
    client = DragonBot()
    assert bot_token is not None
    client.run(bot_token)


if __name__ == "__main__":
    main()
