import discord
from discord.ext import commands
from discord.ext.commands import Context, Cog


class tickets(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="New", aliases=["new"])
    async def new_ticket(self, ctx: Context):
        """Create a new ticket."""
        await ctx.send("Ticket creation is not implemented yet.")

    @commands.command(name="close")
    async def close_ticket(self, ctx: Context):
        """Close the current ticket."""
        await ctx.send("Ticket closing is not implemented yet.")
