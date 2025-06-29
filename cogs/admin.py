from discord import TextChannel
import discord
from discord.ext import commands
from discord.ext.commands import Context, Cog, ExtensionNotFound
from discord.ext.commands.core import ExtensionFailed
from discord.ext.commands.errors import ExtensionAlreadyLoaded, ExtensionNotLoaded
from discord.state import CategoryChannel


class admin(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="load", hidden=True)
    @commands.has_permissions(administrator=True)
    async def load(self, ctx: Context, ext_name: str):
        try:
            await self.bot.load_extension("cogs." + ext_name)
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
    @commands.has_permissions(administrator=True)
    async def unload(self, ctx: Context, ext_name: str):
        if ext_name == "admin":
            return await ctx.send(
                "You cannot unload the admin cog as it contains the load extension command"
            )
        try:
            await self.bot.unload_extension("cogs." + ext_name)
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
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx: Context, ext_name: str):
        try:
            await self.bot.reload_extension("cogs." + ext_name)
        except ExtensionFailed:
            await ctx.send(f"{ext_name} failed loading!")
        except ExtensionNotFound:
            await ctx.send(f"{ext_name} is not a legal extension name!")
        else:
            await ctx.send(f"{ext_name} has been sucessfully reloaded!")
        finally:
            return None

    @commands.command(name="ext_list", hidden=True)
    @commands.has_permissions(administrator=True)
    async def ext_list(self, ctx: Context):
        await ctx.send("All loaded extensions list:\n")
        return await ctx.send(
            "\n".join(s.split("cogs.")[1] for s in self.bot.extensions)
        )

    @commands.command(name="purge_msg", hidden=True, aliases=["purge"])
    @commands.has_permissions(administrator=True)
    async def purge_msg(self, ctx: Context, limit: int):
        try:
            assert isinstance(ctx.channel, TextChannel)
            await ctx.channel.purge(limit=limit)
        except AssertionError:
            return
        else:
            return


async def setup(client):
    await client.add_cog(admin(client))
