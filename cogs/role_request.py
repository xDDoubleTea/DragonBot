from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Context, Cog, ExtensionNotFound
from discord.ext.commands.core import ExtensionFailed
from discord.ext.commands.errors import ExtensionAlreadyLoaded, ExtensionNotLoaded


class RoleRequest(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(client):
    await client.add_cog(RoleRequest(client))
