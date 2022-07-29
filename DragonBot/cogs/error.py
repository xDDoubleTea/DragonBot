import discord 
import random
from discord.ext import commands
from pytube.__main__ import YouTube
import random


Me = 1

class error(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        global Me

        guild = ctx.message.guild
        me = self.client.get_user(Me)
        
        embed = discord.Embed(
            title = f'Error! in {guild.name}',
            description=error,
            color = discord.Colour.from_rgb(190, 119, 255)
        )
        if ctx.message.author != Me:
            await ctx.message.channel.send(embed = embed)

        await me.send(embed=embed)
    


async def setup(client):
    await client.add_cog(error(client))