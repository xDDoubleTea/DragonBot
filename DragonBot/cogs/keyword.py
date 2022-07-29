import discord
from discord import Interaction, Button
from discord.ext import commands
from discord.ui import View, button
from config.bot_info import *
from config.Mysql_info import MySqlDataBase
import math

class KeyChange(discord.ui.Button):
    async def callback(self, interaction):
        await interaction.response.defer()
        channel = interaction.channel
        msg = await channel.send(f'先使用\n`{pre}keyrm <關鍵字>`移除已經在資料庫中的關鍵字\n再使用\n`{pre}key <關鍵字> <回覆>`\n來設置關鍵字!')
        await msg.add_reaction('❗')

class KeyNotChange(discord.ui.Button):
    async def callback(self, interaction):
        await interaction.response.defer()
        msg = await interaction.channel.send('已取消動作!')
        await msg.add_reaction('❗')


class PageTurning(View):
    def __init__(self, client:discord.Client):
        super().__init__(timeout = 600)
        keywords_info = MySqlDataBase()
        sql = 'SELECT * FROM keyword'
        keyword_info = keywords_info.get_db_data(sql_cmd = sql)
        self.keywords:list = keyword_info
        self.totalPages:int = math.ceil(len(keyword_info)/10)
        if self.totalPages > 0:
            self.now_page:int = 1
        else:
            self.now_page:int = 0
        self.client = client

    async def to_embed(self, gnd, lim):
        embed = discord.Embed(
            title = '關鍵字',
            description = f'{pre}key <關鍵字> <回覆>',
            color = theme_color
        )
        for i in range(gnd, lim):
            embed.add_field(name = f'#{i+1} 關鍵字{self.keywords[i][0]}', value = f'回覆 : {self.keywords[i][1]}', inline = False)

        dev = self.client.get_user(My_user_id)
        embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
        embed.set_footer(text = f"第{self.now_page}/{self.totalPages}頁", icon_url=dev.avatar.url)
        return embed


    async def get_keywords(self):
        gnd = 0
        lim = 0
        if len(self.keywords) > 10:
            gnd = int((self.now_page-1)*10)
            if len(self.keywords) - gnd >= 10:
                lim = int(gnd+10)
            else:
                lim = len(self.keywords)
        else:
            gnd = 0
            lim = len(self.keywords)-1
        return await self.to_embed(gnd = gnd, lim = lim)
            
    @button(label = '上一頁', style = discord.ButtonStyle.blurple, emoji = '◀️')
    async def pre_callback(self, interaction:Interaction, button:Button):
        page = int(interaction.message.embeds[0].footer.text.split('/')[0][1])
        if page > 1:
            page -= 1
        else:
            pass
        self.now_page = page
        await interaction.message.edit(view = self)
        return await interaction.response.edit_message(embed = await self.get_keywords())
         

    @button(label = '下一頁', style = discord.ButtonStyle.blurple, emoji = '▶️')
    async def next_callback(self, interaction:Interaction, button:Button):
        page = int(interaction.message.embeds[0].footer.text.split('/')[0][1])
        if page < self.totalPages:
            page += 1
        else:
            pass
        self.now_page = page
        await interaction.message.edit(view = self)
        return await interaction.response.edit_message(embed = await self.get_keywords())


class keyword(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(name = "keyword", aliases = ['key', 'word'])
    async def keyword(self, ctx, word, response):
        if ctx.author.guild_permissions.administrator:
            sql = 'SELECT * from keyword'
            data = MySqlDataBase().get_db_data(sql_cmd = sql)
            has_word = False
            if len(data) > 0:
                for x in data:
                    if x[0] == word:
                        has_word = True
                        break

            if has_word:
                v = View(timeout = None)
                yesbtn = KeyChange(
                    style = discord.ButtonStyle.green,
                    label = '是',
                    custom_id=None,
                    disabled= False
                )
                nobtn = KeyNotChange(
                    style = discord.ButtonStyle.red,
                    label = '否',
                    custom_id=None,
                    disabled = False
                )
                v.add_item(yesbtn)
                v.add_item(nobtn)
                await ctx.message.channel.send(f"{word}已經在資料庫中,你想要做更動嗎?", view = v)

            else:   
                sql = 'INSERT INTO keyword (words, response) VALUES (%s, %s)'
                val = (word, response)
                data = MySqlDataBase().get_db_data(sql_cmd = sql, values = val)
                msg = await ctx.message.channel.send(f"{word}加入成功!")
                await msg.add_reaction('✅')
                
        else:
            msg = await ctx.message.channel.send(f'{ctx.user.mention}無權限使用此指令!')
            await msg.add_reaction('❌')

    @commands.command(name = 'keywordremove', aliases = ['keyrm', 'wordrm'])
    async def keywordremove(self, ctx, word):
        if ctx.author.guild_permissions.administrator:

            sql = 'SELECT * from keyword'
            data = MySqlDataBase().get_db_data(sql_cmd = sql)

            has_word = False
            for x in data:
                if x[0] == word:
                    has_word = True
                    break
                

            if has_word:
                sql = "DELETE FROM keyword WHERE words = %s"
                val = (word, )
                MySqlDataBase().del_data(sql_cmd=sql, values = val)
                msg = await ctx.message.channel.send(f'已移除關鍵字{word}!')
                await msg.add_reaction('✅')
            else:
                msg = await ctx.message.channel.send(f'未找到關鍵字{word}!，使用{pre}keywordlist或{pre}keylist來得知目前資料庫中之關鍵字!')
                await msg.add_reaction('❌')
        else:
            msg = await ctx.message.channel.send(f'{ctx.user.mention}無權限使用此指令!')
            await msg.add_reaction('❌')
    
    @commands.command(name = 'keywordslist', aliases = ['keylist', 'wordlist'])
    async def keywordslist(self ,ctx, mode = 1):
        if ctx.author.guild_permissions.administrator:
            #mode = 1:訊息傳於觸發指令頻道內，mode = 2:私訊
            sql = 'SELECT * from keyword'
            data = MySqlDataBase().get_db_data(sql_cmd = sql)
            embed = await PageTurning(client = self.client).get_keywords()
            if len(data) > 0:
                if mode == 1:
                    await ctx.send(embed = embed, view = PageTurning(client = self.client))
                elif mode == 2:
                    await ctx.message.author.send(embed = embed, view = PageTurning(client = self.client))
                else:
                    msg = await ctx.message.channel.send('無此訊息傳送模式!訊息傳送模式:(1為在觸發指令之頻道內傳送，2為私訊觸發指令之使用者)')
                    await msg.add_reaction('❌')
            else:
                msg = await ctx.send(f'資料庫中無關鍵字!使用`{pre}key <關鍵字> <回覆>`來新增關鍵字!')
                await msg.add_reaction('❗')
        else:
            msg = await ctx.message.channel.send(f'{ctx.user.mention}無權限使用此指令!')
            await msg.add_reaction('❌')


    @keyword.error
    async def key_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = await ctx.send(f'指令輸入錯誤!使用方式`{pre}key <關鍵字> <回覆>`!')
            await msg.add_reaction('❌')

    @keywordremove.error
    async def keyrm_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            msg = await ctx.send(f'指令輸入錯誤!使用方式`{pre}keyrm <關鍵字>`!')
            await msg.add_reaction('❌')





async def setup(client):
    await client.add_cog(keyword(client))