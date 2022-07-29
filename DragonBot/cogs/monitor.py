import discord
from discord.ext import commands
import os, psutil

class monitor(commands.Cog):

    @commands.command(name = 'Ram',aliases = ['ram'])
    async def Ram(self, ctx):
        process = psutil.Process(os.getpid())
        embed = discord.Embed(
            title = 'RAM usage',
            description = f'The RAM usage is:`{(process.memory_info().rss)/(1024*1024)}`MB',
            color=discord.Colour.from_rgb(190, 119, 255)
        )
        await ctx.channel.send(embed=embed)
    
    @commands.command(name='CPU',aliases=['cpu'])
    async def CPU(self, ctx):
        embed = discord.Embed(
            title = 'CPU usage',
            description = '💤 | testing...',
            color=discord.Colour.from_rgb(190, 119, 255)
        )
        msg = await ctx.channel.send(embed=embed)
        test_cpu = psutil.cpu_percent(2)
        if test_cpu > 70:
            desc = f'❗ | The CPU usage is:`{test_cpu}`%'
        else:
            desc = f'✅ | The CPU usage is:`{test_cpu}`%'
        embed = discord.Embed(
            title = 'CPU usage',
            description = desc,
            color=discord.Colour.from_rgb(190, 119, 255)
        )
        await msg.edit(embed=embed)

async def setup(client):
    await client.add_cog(monitor(client))