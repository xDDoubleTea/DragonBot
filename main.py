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
from config.constants import DRAGONSHOP_API_SECRET_KEY, WORDPRESS_URL
from core.feedback_manager import FeedbackManager
from core.role_requesting_manager import RoleRequestManager
from core.ticket_manager import TicketManager
from core.keyword_manager import KeywordManager
from core.ticket_panel_manager import TicketPanelManager
from db.database_manager import AsyncDatabaseManager, DatabaseManager
import logging
from utils.logger import setup_logging
from adapters.wordpress_client import WordPressClient

setup_logging()
logger = logging.getLogger(__name__)


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
        # Maybe we will need the Synchrounus database manager one day.
        assert DRAGONSHOP_API_SECRET_KEY
        self.wordpress_client = WordPressClient(
            api_url=WORDPRESS_URL, api_key=DRAGONSHOP_API_SECRET_KEY
        )
        self.async_db_manager = AsyncDatabaseManager(db_url=db_url)
        self.feedback_manager = FeedbackManager(
            bot=self, database_manager=self.async_db_manager
        )
        self.ticket_manager = TicketManager(
            bot=self,
            database_manager=self.async_db_manager,
            feedback_manager=self.feedback_manager,
            wordpress_client=self.wordpress_client,
        )
        self.ticket_panel_manager = TicketPanelManager(
            bot=self, database_manager=self.async_db_manager
        )
        self.keyword_manager = KeywordManager(
            bot=self, database_manager=self.async_db_manager
        )
        self.role_request_manager = RoleRequestManager(
            bot=self, database_manager=self.async_db_manager
        )

    async def on_ready(self):
        print(f"{self.user} is now online!")
        await self.change_presence(
            activity=discord.Game(f"Developed by {self.get_user(My_user_id)}")
        )
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def setup_hook(self):
        await self.async_db_manager.connect()
        print("Connected to the database")
        await self.keyword_manager.initialize_cache()
        print("Keyword cache initialized")
        print("Initializing role request data cache")
        await self.role_request_manager.init_cache()
        print("Role request data cache initialized")
        await self.ticket_manager.init_cache()
        for cog in filter(
            lambda file: file.endswith(".py"),
            os.listdir("./cogs"),
        ):
            await self.load_extension(f"cogs.{cog[:-3]}")

    async def close(self):
        await self.async_db_manager.close()
        await super().close()


def main():
    client = DragonBot()
    assert bot_token is not None
    client.run(bot_token)


if __name__ == "__main__":
    main()
