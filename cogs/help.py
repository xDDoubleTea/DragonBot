from discord import Client
from discord.ext.commands import Bot, Cog

from main import DragonBot


class HelpCog(Cog):
    def __init__(self, bot: Client | Bot):
        self.bot = bot


async def setup(client: DragonBot):
    await client.add_cog(HelpCog(bot=client))
