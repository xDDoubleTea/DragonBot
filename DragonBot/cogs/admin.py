import discord
from discord.ext import commands
import random
import os
import time
from datetime import date
from config.bot_info import *

Me = My_user_id

class admin(commands.Cog):
    def __init__(self, client):
        self.client = client
    

    @commands.command()
    @commands.has_permissions(manage_messages = True)
    async def delmes(self, ctx, amount = 2):
        await ctx.channel.purge(limit = amount + 1)

    
    @commands.command(aliases = ["ld"], help = "<ADMIN only command> Load extension")
    @commands.has_permissions(administrator = True)
    async def load(self, ctx, extension):
        if extension != 'admin':
            try:
                if str(extension) == "all" or str(extension) == "All":
                    for filename in os.listdir('./cogs'):
                        if filename.endswith('.py'):
                            await self.client.load_extension(f'cogs.{filename[:-3]}')
                else:
                    await self.client.load_extension(f'cogs.{extension}')
                    await ctx.send(f'{extension} was loaded successfully!')
            except:
                await ctx.send(f"{extension} has already been loaded or doesn't exsit")
        else:
            await ctx.send("You can't load admin")

    @commands.command(aliases = ["unld"], help = "<ADMIN only command> Unload extension")
    @commands.has_permissions(administrator = True)
    async def unload(self, ctx, extension):
        if extension != 'admin':
            try:
                if str(extension) == "all" or str(extension) == "All":
                    for filename in os.listdir('./cogs'):
                        if filename.endswith('.py'):
                            await self.client.unload_extension(f'cogs.{filename[:-3]}')
                else:
                    await self.client.unload_extension(f'cogs.{extension}')
                    await ctx.send(f'{extension} was unloaded successfully!')
            except:
                await ctx.send(f"{extension} has already been unloaded or doesn't exsit")
        else:
            await ctx.send("You can't unload admin")

    @commands.command(aliases = ["reld"], help = "<ADMIN only command> Reload extension")
    @commands.has_permissions(administrator = True)
    async def reload(self, ctx, extension):
        if extension != 'admin':
            try:
                await self.client.unload_extension(f'cogs.{extension}')
                await self.client.load_extension(f'cogs.{extension}')
                await ctx.send(f'{extension} was reloaded successfully!')
            except:
                await ctx.send(f"{extension} doesn't exsit")
        else:
            await ctx.send("You can't reload admin")

    @commands.command(aliases = ["extlist"], help = "<ADMIN only command> Lists the extensions available")
    @commands.has_permissions(administrator = True)
    async def extensionlist(self ,ctx):
        number = 0
        listembed = discord.Embed(
            title = "List of available extensions",
            description = "Returns the list",
            color = discord.Colour.blue()
        )
        t = time.localtime()
        today = date.today()
        today_date = today.strftime("%Y/%m/%d")
        current_time = time.strftime("%H:%M:%S", t)
        for filename in os.listdir('./cogs'):
            number += 1
            if filename.endswith('.py'):
                listembed.add_field(name = f"{number}", value = f"{filename[:-3]}", inline = False)
        listembed.set_footer(text = f"{default_footer} \n Sent at {today_date} , {current_time}")
        await ctx.send(embed = listembed)

    @commands.command(name='say', aliases =['s'])
    async def say(self, ctx):
        if ctx.message.author.id == Me:
            content = ctx.message.content[3:]
            await ctx.message.delete()
            await ctx.message.channel.send(content)
        else:
            await ctx.message.channel.send("You don't have access to this command.")

    @delmes.error
    async def delmes_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f'{ctx.author} has no access to this command')

async def setup(client):
    await client.add_cog(admin(client))