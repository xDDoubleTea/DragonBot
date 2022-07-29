import discord
from discord import Interaction
from discord.ext import commands
from discord.ui import View, Button, button
import math
from config.Mysql_info import MySqlDataBase
from config.bot_info import *
from config.Sorting import quicksorting


class PageTurning(View):
    def __init__(self, client:discord.Client):
        super().__init__(timeout = 600)
        money_info = MySqlDataBase()
        sql = 'SELECT * FROM money'
        money_info = money_info.get_db_data(sql_cmd = sql)
        self.user_money:list = money_info
        self.totalPages:int = math.ceil(len(money_info)/10)
        if self.totalPages > 0:
            self.now_page:int = 1
        else:
            self.now_page:int = 0
        self.client = client

    async def to_embed(self, desc:str):
        embed = discord.Embed(
            title = '龍龍幣排行榜',
            description = desc,
            color = theme_color
        )
        dev = self.client.get_user(My_user_id)
        embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
        embed.set_footer(text = f"第{self.now_page}/{self.totalPages}頁", icon_url=dev.avatar.url)
        return embed


    async def get_money_leaderboard(self):
        desc = ''
        if len(self.user_money) > 10:
            sorted_money = quicksorting().quicksort(self.user_money, 0, len(self.user_money)-1)
            sorted_money.reverse()
            gnd = int((self.now_page-1)*10)
            if len(self.user_money) - gnd >= 10:
                lim = int(gnd+10)
            else:
                lim = len(self.user_money)
            output_info = []
            for i in range(gnd, lim):
                output_info.append(sorted_money[i])
            
            for i,info in enumerate(sorted_money, gnd):
                desc += f'#{i+1}:{self.client.get_user(int(info[0])).mention}'
                desc += '-------'
                desc += f'${info[1]}💰\n'
        elif len(self.user_money) > 2:
            sorted_money = quicksorting().quicksort(self.user_money, 0, len(self.user_money)-1)
            sorted_money.reverse()
            for i,info in enumerate(sorted_money):
                desc += f'#{i+1}:{self.client.get_user(int(info[0])).mention}'
                desc += '-------'
                desc += f'${info[1]}💰\n'
        elif len(self.user_money) == 2:
            money = []
            for money_num in self.user_money:
                money.append(money_num[1])
            if money[0] < money[1]:
                self.user_money[0] , self.user_money[1] = self.user_money[1] , self.user_money[0]
            sorted_money = self.user_money
            for i,info in enumerate(sorted_money):
                desc += f'#{i+1}:{self.client.get_user(int(info[0])).mention}'
                desc += '-------'
                desc += f'${info[1]}💰\n'
        else:
            pass    
        return await self.to_embed(desc = desc)
            

    @button(label = '上一頁', style = discord.ButtonStyle.blurple, emoji = '◀️')
    async def pre_callback(self, interaction:Interaction, button:Button):
        page = int(interaction.message.embeds[0].footer.text.split('/')[0][1])
        if page > 1:
            page -= 1
        else:
            pass
        self.now_page = page
        await interaction.message.edit(view = self)
        return await interaction.response.edit_message(embed = await self.get_money_leaderboard())
         

    @button(label = '下一頁', style = discord.ButtonStyle.blurple, emoji = '▶️')
    async def next_callback(self, interaction:Interaction, button:Button):
        page = int(interaction.message.embeds[0].footer.text.split('/')[0][1])
        if page < self.totalPages:
            page += 1
        else:
            pass
        self.now_page = page
        await interaction.message.edit(view = self)
        return await interaction.response.edit_message(embed = await self.get_money_leaderboard())

class moneysys(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.command(name='add_money',aliases=['add_coin'])
    @commands.has_permissions(administrator = True)
    async def add_money(self, ctx, user_id:int, amount:int):
        data = MySqlDataBase()
        sql = 'SELECT * FROM money'
        money_info = data.get_db_data(sql_cmd=sql)
        
        has_user = False
        index = 0
        for x,i in enumerate(money_info):
            if i[0] == str(user_id):
                has_user = True
                index = x
                break

        user_money = 0
        user = self.client.get_user(user_id)
        if user == None:
            return await ctx.send('查無此人')

        if has_user:
            user_money = int(money_info[index][1])
            user_money += amount
            db = MySqlDataBase()
            sql = 'UPDATE money SET money = %s WHERE user_id = %s'
            val = (user_money, str(user.id))
            db.update_data(sql_cmd=sql, values = val)
            if amount > 0:
                await ctx.channel.send(f'成功幫{user.mention}加入了{amount}龍龍幣!{user.mention}現在有{user_money}龍龍幣💰!')
            elif amount < 0:
                amount = str(amount)
                await ctx.channel.send(f'成功幫{user.mention}移除了{amount[1:]}龍龍幣!{user.mention}現在有{user_money}龍龍幣💰!')
            elif amount == 0:
                await ctx.channel.send(f'{user.mention}的龍龍幣還是{user_money}龍龍幣💰!')
        else:
            db = MySqlDataBase()
            user_money += amount
            sql = 'INSERT INTO money (user_id, money) VALUES (%s, %s)'
            val = (str(user.id) ,user_money)
            db.insert_data(sql_cmd=sql, values = val)
            if amount > 0:
                await ctx.channel.send(f'成功幫{user.mention}加入了{amount}龍龍幣!{user.mention}現在有{user_money}龍龍幣💰!')
            elif amount < 0:
                amount = str(amount)
                await ctx.channel.send(f'成功幫{user.mention}移除了{amount[1:]}龍龍幣!{user.mention}現在有{user_money}龍龍幣💰!')
            elif amount == 0:
                await ctx.channel.send(f'{user.mention}的龍龍幣還是{user_money}龍龍幣💰!')            


    @commands.command(name='money_search', aliases =['money'])
    async def money_search(self, ctx, user_id:int = 0 ):
        if user_id != 0:
            sql = 'SELECT * FROM money'
            db = MySqlDataBase()
            money_info = db.get_db_data(sql_cmd = sql)
            user = self.client.get_user(user_id)
            if user == None:
                return await ctx.send('查無此人')

            has_user = False
            index = 0
            for x,i in enumerate(money_info):
                if i[0] == str(user.id):
                    index = x 
                    has_user = True
                    break
            
            if has_user:
                user_money = money_info[index][1]
                await ctx.channel.send(f'{user.mention}現在有{user_money}龍龍幣💰!')
            else:
                await ctx.channel.send(f'{user.mention}還沒有龍龍幣帳戶！')
        else:
            sql = 'SELECT * FROM money'
            db = MySqlDataBase()
            money_info = db.get_db_data(sql_cmd = sql)
            user = ctx.message.author
            has_user = False
            index = 0
            for x,i in enumerate(money_info):
                if i[0] == str(user.id):
                    index = x 
                    has_user = True
                    break
                
            if has_user:
                user_money = money_info[index][1]
                await ctx.channel.send(f'{user.mention}現在有{user_money}龍龍幣!')
            else:
                await ctx.channel.send(f'{user.mention}還沒有龍龍幣帳戶！')    
        
    @commands.command(name = 'money_list', aliases = ['coinslist'])
    async def money_list(self, ctx):
        page_turning = PageTurning(client = self.client)
        new_embed = await page_turning.get_money_leaderboard()
        return await ctx.send(embed = new_embed, view = page_turning)
                
async def setup(client):
    await client.add_cog(moneysys(client))