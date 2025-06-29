from discord.ext import commands
from discord.ext.commands import Context, Cog, ExtensionNotFound
from discord.ext.commands.core import ExtensionFailed
from discord.ext.commands.errors import ExtensionAlreadyLoaded, ExtensionNotLoaded


class admin(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="load", hidden=True)
    async def load(self, ctx: Context, ext_name: str):
        try:
            await self.bot.load_extension(ext_name)
        except ExtensionAlreadyLoaded:
            await ctx.send(f"{ext_name} has already been loaded!")
        except ExtensionFailed:
            await ctx.send(f"{ext_name} failed loading!")
        except ExtensionNotFound:
            await ctx.send(f"{ext_name} is not a legal extension name!")
        else:
            await ctx.send(f"{ext_name} has been sucessfully loaded!")
        finally:
            return None

    @commands.command(name="unload", hidden=True)
    async def unload(self, ctx: Context, ext_name: str):
        try:
            await self.bot.unload_extension(ext_name)
        except ExtensionNotLoaded:
            await ctx.send(f"{ext_name} wasn't loaded!")
        except ExtensionFailed:
            await ctx.send(f"{ext_name} failed unloading!")
        except ExtensionNotFound:
            await ctx.send(f"{ext_name} is not a legal extension name!")
        else:
            await ctx.send(f"{ext_name} has been sucessfully unloaded!")
        finally:
            return None

    @commands.command(name="reload", hidden=True)
    async def reload(self, ctx: Context, ext_name: str):
        try:
            await self.bot.load_extension(ext_name)
        except ExtensionFailed:
            await ctx.send(f"{ext_name} failed loading!")
        except ExtensionNotFound:
            await ctx.send(f"{ext_name} is not a legal extension name!")
        else:
            await ctx.send(f"{ext_name} has been sucessfully reloaded!")
        finally:
            return None

    @commands.command(name="ext_list", hidden=True)
    async def ext_list(self, ctx: Context):
        await ctx.send("All loaded extensions list:\n")
        return await ctx.send("\n".join(self.bot.extensions))


async def setup(client):
    await client.add_cog(admin(client))
