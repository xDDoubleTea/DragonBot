import discord
from discord.ext import commands    
from config.bot_info import *
    
class bug_reporting(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.command(name='bug_report', aliases=['bug', 'report'])
    async def bug_report(self, ctx, *, data):
        with open('bug_id.json') as file:
            bug_id = json.load(file)['bug_id']
        
        msg:discord.Message = await get_embed.send_bug_embed(self = self, ctx = ctx, bug_id = bug_id, data = data)
        if len(ctx.message.attachments) > 0:
            files = []
            for attachment in ctx.message.attachments:
                files.append(await attachment.to_file())
            
            await msg.edit(attachments = files)
        

    @commands.command(name='bug_edit', aliases=['buge'])
    async def bug_edit(self, ctx, *, data):
        bug_id = data.split(', ')[0] 
        if ctx.message.author.id == My_user_id:
            logs_channel = self.client.get_channel(logchannel)
            msgs = [message async for message in logs_channel.history(limit=50)]
            edit_msg = 0
            for x in msgs:
                if x.content == bug_id:
                    edit_msg = x
                    break
            
            if edit_msg != 0:
                raw_embed = discord.Embed.to_dict(edit_msg.embeds[0])
                bug_stats = raw_embed['fields'][3]['value']
                new_stats = data.split(', ')[1]

                if bug_stats != new_stats:
                    raw_embed['fields'][3]['value'] = new_stats
                    embed = discord.Embed.from_dict(raw_embed)
                    await edit_msg.edit(embed = embed)
                    return await ctx.message.channel.send(f'Bug stats with the bug_id of `{bug_id}` has been changed from `{bug_stats}` to `{new_stats}`')
                else:
                    return await ctx.message.channel.send(f'Bug stats with the bug_id of `{bug_id}` had already been set to `{new_stats}`')
            else:
                return await ctx.channel.send('No such bug exsit!')

    @commands.command(name='bug_remove', aliases = ['bug_rm'])
    async def bug_remove(self, ctx, bug_id):
        if ctx.message.author.id == My_user_id:
            logs_channel = self.client.get_channel(logchannel)
            msgs = [message async for message in logs_channel.history(limit=None)]
            del_msg = 0
            for x in msgs:
                if x.content == bug_id:
                    del_msg = x
                    break   
            if del_msg != 0:
                await del_msg.delete()
                return await ctx.channel.send(f'Bug with bug_id = {bug_id} has been removed!') 
            else:
                return await ctx.message.channel.send('No such bug exists')


async def setup(client):
    await client.add_cog(bug_reporting(client = client))