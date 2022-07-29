import discord 
from discord.ext import commands
from config.Mysql_info import *
from config.bot_info import *
from config.feedback import *
import json

class main_cmd(commands.Cog):
    def __init__(self, client:discord.Client):
        super().__init__()
        self.client = client

    @commands.command(name = 'help', aliases = ['h'])
    async def help(self, ctx, cmd = '0'):
        return await get_embed.help_embed(
            self = self, 
            message = ctx.message,
            cmd = cmd
        )

    @commands.command(name = 'get_emoji')
    async def get_emoji(self, ctx):
        print(ctx.guild.emojis)

    @commands.command(name = "USD", aliases = ["U", "usd"])
    async def usd_convert(self ,ctx , usd):
        output = 0
        usd = float(usd)
        if usd > 33:
            output = usd*30 +60
        elif 0 < usd <= 33:
            output = usd*30 +40
        else:
            msg = await ctx.send(f'錯誤!正確使用方式:`{pre}usd <number>`')
            await msg.add_reaction('❌')
            return

        msg = await ctx.send(f'NTD{pre}{output}')
        await msg.add_reaction('💱')

    @commands.command(name = "EUR", aliases = ["E", "eur"])
    async def eur_convert(self ,ctx , eur):
        output = 0
        eur = float(eur)
        if eur > 30:
            output = eur*35 + 50
        elif 0 < eur <= 30:
            output = eur*30 + 30
        else:
            msg = await ctx.send(f'錯誤!正確使用方式:`{pre}eur <number>`')
            await msg.add_reaction('❌')
            return

        msg = await ctx.send(f'NTD{pre}{output}')
        await msg.add_reaction('💱')
    
    @commands.command(name='update_log', aliases = ['u_l'])
    @commands.dm_only()
    async def update_log(self, ctx, *, msg):
        if ctx.message.author.id == 398444155132575756:
            logs_channel = self.client.get_channel(977445485180751882)
            send_msg = msg
            if len(ctx.message.stickers) > 0:
                for i in ctx.message.stickers:
                    send_msg += i.url
            
            sent = await logs_channel.send(send_msg)
            file = []
            if len(ctx.message.attachments) > 0:
                for attach in ctx.message.attachments:
                    file.append(await attach.to_file())
                
                await sent.edit(attachments = file)
            
            await sent.add_reaction('✅')
            await ctx.message.author.send('Message sent!')
        else:
            return


    @commands.command()
    async def ping(self, ctx):
        await ctx.message.channel.send(f'{round(self.client.latency * 1000)}ms')


async def setup(client):
    await client.add_cog(main_cmd(client = client))