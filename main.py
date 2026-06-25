import asyncio
import os
import logging
import discord
from discord.ext import commands
from config import (
    pre,
    app_id,
    bot_token,
    MY_USER_ID,
    VERSION,
    app_mode,
    db_url,
    MY_GUILD,
)
from core.feedback_manager import FeedbackManager
from core.role_requesting_manager import RoleRequestManager
from core.ticket_manager import TicketManager
from core.keyword_manager import KeywordManager
from core.ticket_panel_manager import TicketPanelManager
from db.database_manager import AsyncDatabaseManager, DatabaseManager
import signal
from config.logger import setup_logger


class DragonBot(commands.Bot):
    def __init__(self, intents: discord.Intents, logger: logging.Logger):
        assert pre is not None, "Prefix must be defined in the config"
        super().__init__(
            command_prefix=pre,
            intents=intents,
            help_command=None,
            description=f"Dragon Bot version {VERSION}\n Mode {app_mode}",
            application_id=app_id,
        )
        assert db_url is not None
        self.logger = logger

        self.db_manager = DatabaseManager(database_url=db_url)
        # Maybe we will need the Synchrounus database manager one day.

        self.async_db_manager = AsyncDatabaseManager(db_url=db_url)
        self.feedback_manager = FeedbackManager(
            bot=self, database_manager=self.async_db_manager
        )
        self.ticket_manager = TicketManager(
            bot=self,
            database_manager=self.async_db_manager,
            logger=self.logger,
            feedback_manager=self.feedback_manager,
        )
        self.ticket_panel_manager = TicketPanelManager(
            bot=self, database_manager=self.async_db_manager, logger=self.logger
        )
        self.keyword_manager = KeywordManager(
            bot=self, database_manager=self.async_db_manager
        )
        self.role_request_manager = RoleRequestManager(
            bot=self, database_manager=self.async_db_manager
        )

    async def on_ready(self):
        self.logger.info(f"{self.user} is now online!")
        await self.change_presence(
            activity=discord.Game(f"Developed by {self.get_user(MY_USER_ID)}")
        )
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def setup_hook(self):
        await self.async_db_manager.connect()
        self.logger.debug("Connected to the database")
        await self.keyword_manager.initialize_cache()
        self.logger.debug("Keyword cache initialized")
        self.logger.debug("Initializing role request data cache")
        await self.role_request_manager.init_cache()
        self.logger.debug("Role request data cache initialized")
        await self.ticket_manager.init_cache()
        for cog in filter(
            lambda file: file.endswith(".py"),
            os.listdir("./cogs"),
        ):
            await self.load_extension(f"cogs.{cog[:-3]}")

    async def close(self):
        await self.async_db_manager.close()
        await super().close()


async def close_client(client: commands.Bot):
    await client.close()


async def main():
    async def shutdown(sig: signal.Signals, loop: asyncio.AbstractEventLoop):
        if sig:
            bot.logger.info(f"Received exit signal {sig.name}...")

        for task in asyncio.all_tasks(loop):
            task.cancel()
            bot.logger.info(f"Cancelling task {task.get_name()}...")

        await bot.close()
        bot.logger.info("Shutdown complete.")
        loop.stop()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )

    log_level = logging.DEBUG if app_mode == "test" else logging.INFO
    setup_logger(log_level=log_level)

    intents = discord.Intents.all()
    bot = DragonBot(intents=intents, logger=logging.getLogger("DragonBot"))

    try:
        await bot.start(token=bot_token)
    except asyncio.CancelledError:
        bot.logger.info("Bot shutdown initiated...")
    except Exception as e:
        bot.logger.exception("An unhandled error occurred:", exc_info=e)
    finally:
        if not bot.is_closed():
            await bot.close()
            bot.logger.info("Bot closed.")


if __name__ == "__main__":
    asyncio.run(main())
