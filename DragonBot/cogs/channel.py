import discord
from discord import Interaction
from discord.ext import commands
from discord.ui import View, button, select, Button
import emoji
from numpy import save
import chat_exporter
import io
import json
from config.bot_info import *
from config.feedback import *
from config.Mysql_info import *
from typing import List

class OpenButtons(View):
    class btnInfo:
        def __init__(self, channel_name:str):
            self.channel_name = channel_name
    def __init__(self, client:discord.Client):
        super().__init__(timeout = None)
        self.client = client
        #從資料庫取出channel_info並轉為可用的形式 -> [(List[discord.User],discord.TextChannel)]
        sql_cmd = 'SELECT * FROM customers'
        raw_data = MySqlDataBase.get_db_data(self = MySqlDataBase(),sql_cmd = sql_cmd)
        channel_count = 0
        all_channel = []
        for index, channel_id in enumerate(raw_data):
            if index == 1:
                pass
            else:
                if channel_id != raw_data[index-1][1]:
                    channel_count += 1
                    all_channel.append(raw_data[index-1][1])
                else:
                    pass
        channel_info_list = []
        for channel in all_channel:
            new_tuple = ([],self.client.get_channel(int(channel)))
            for customer in raw_data:
                if customer[1] == channel:
                    new_tuple[0].append(self.client.get_user(int(customer[0])))

            channel_info_list.append(new_tuple)
            
        self.channel_info:list = channel_info_list
        with open('channel_name.json', 'r') as file:
            name = json.load(file)
        self.channel_name:str = name['channel_name']
        
        

    def set_new_channel_name(self):
        self.channel_name = int(self.channel_name)
        self.channel_name += 1
        digit = 0
        tmp = self.channel_name
        while tmp >= 1:
            tmp/=10
            digit += 1

        zeros = 4 - digit
        zero = ''
        if zeros > 0:
            for i in range(zeros):
                zero += '0'
            zero += str(self.channel_name)
            self.channel_name = zero
            with open('channel_name.json', 'w') as file:
                json.dump({"channel_name":self.channel_name}, file, indent = 4)
        else:
            self.channel_name = str(self.channel_name)
            with open('channel_name.json', 'w') as file:
                json.dump({"channel_name":self.channel_name}, file, indent = 4)

    async def open_text_channel(self, interaction:discord.Interaction, button:Button):
        #set permissions
        #customer service role 
        cus_service_role = interaction.guild.get_role(cus_service_role_id)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        }
        #create new channel
        new_channel = await interaction.guild.create_text_channel(name = f'{button.custom_id}-{self.channel_name}', overwrites = overwrites)
        perms = new_channel.overwrites_for(cus_service_role)
        perms.read_messages = True
        await new_channel.set_permissions(cus_service_role ,overwrite = perms)

        #set next channel name
        self.set_new_channel_name()
        customers = []
        customers.append(interaction.user)
        self.channel_info.append((customers, new_channel))

        for cus in customers:
            sql_cmd = 'INSERT INTO customers (customer_id, channel_id) VALUES (%s, %s)'
            val = (str(cus.id), str(new_channel.id))
            MySqlDataBase.insert_data(self = MySqlDataBase(), sql_cmd = sql_cmd, values = val)

        await new_channel.send(
            content = open_cnl_msg(interaction = interaction, cus_service_role = cus_service_role)[0], 
            view = CloseToggle(main = self),
            embed = open_cnl_msg(interaction = interaction, cus_service_role = cus_service_role)[1]
        )
        return await interaction.response.send_message(
            content=f'建立了一個新頻道!{new_channel.mention}', 
            ephemeral = True
        )

    
    @button(label = '代購問題', style = discord.ButtonStyle.blurple, custom_id = '代購')
    async def pur_callback(self, interaction:Interaction, button:Button):
        if button.emoji == None:
            button.emoji = await interaction.guild.fetch_emoji(ds01)
        await interaction.message.edit(view = self)
        return await self.open_text_channel(interaction = interaction, button = button)

    @button(label = '群組問題', style = discord.ButtonStyle.blurple, custom_id = '群組')
    async def guild_callback(self, interaction, button:Button):
        if button.emoji == None:
            button.emoji = await interaction.guild.fetch_emoji(discord_emoji)
        await interaction.message.edit(view = self)
        return await self.open_text_channel(interaction = interaction, button = button)

    @button(label = '其他問題', style = discord.ButtonStyle.blurple, custom_id = '其他', emoji = '📩')
    async def others_callback(self, interaction, button:Button):
        return await self.open_text_channel(interaction = interaction, button = button)

class CloseToggle(View):
    def __init__(self, main:OpenButtons):
        super().__init__(timeout=None)
        self.main = main

    @button(label = '關閉頻道', style = discord.ButtonStyle.blurple)
    async def callback(self, interaction: Interaction, button:Button):
        await interaction.message.edit(view = None)
        return await interaction.response.send_message(
            content='你確定你想要關閉此頻道?', 
            view = CloseButtons(main = self.main)
        )
    
class CloseButtons(View):
    def __init__(self, main:OpenButtons):
        super().__init__(timeout = None)
        self.main = main

    async def close_channel(self, interaction:discord.Interaction):
        #set customers permissions so they no longer can see the channel
        await interaction.message.edit(view = None)
        cus = []
        for info in self.main.channel_info:
            if info[1] == interaction.channel:
                for customers in info[0]:
                    try:
                        perms = interaction.channel.overwrites_for(customers)
                        perms.read_messages = False
                        await interaction.channel.set_permissions(customers, overwrite = perms)
                    except:
                        pass
                cus = info[0]
        #send message with 'delete channel', 'save channel', 'reopen channel' buttons
        #send user with feed back stuff

        await interaction.response.send_message(
            content = f'頻道已被{interaction.user}關閉!接下來你想要?', 
            view = afterClose(main = self.main)
        )
        return await feedbackEmbed(
            channel = interaction.channel,
            client = interaction.client,
            customers = cus,
            view = FeedBackSystem()
        )
    
    @button(label = '關閉頻道', style = discord.ButtonStyle.danger)
    async def close_callback(self, interaction: Interaction, button:Button):
        return await self.close_channel(interaction = interaction)

    @button(label = '取消', style = discord.ButtonStyle.gray)
    async def cancel_callback(self, interaction:Interaction, button:Button):
        await interaction.message.edit(view = None)
        await interaction.response.send_message('已取消關閉!')
        return await interaction.message.edit(view = CloseToggle(main = self.main))

class afterClose(View):
    def __init__(self, main:OpenButtons):
        super().__init__(timeout = None)
        self.main = main
    
    @button(label = '儲存頻道', style = discord.ButtonStyle.blurple)
    async def save_callback(self, interaction:Interaction, button:Button):
        await interaction.response.defer()
        channel = interaction.channel
        async with channel.typing():
            transcript = await chat_exporter.export(interaction.channel)
            transcript_file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"{interaction.channel.name}.html"
                )        
            await channel.send(file=transcript_file)

    @button(label = '刪除頻道', style = discord.ButtonStyle.red)
    async def del_callback(self, interaction:Interaction, button:Button):
        await interaction.response.defer()
        for index, channel in enumerate(self.main.channel_info):
            if channel[1] == interaction.channel:
                self.main.channel_info.pop(index)
                sql_cmd = 'DELETE FROM customers WHERE channel_id = %s'
                val = (str(channel[1].id),)
                MySqlDataBase.del_data(self = MySqlDataBase(), sql_cmd = sql_cmd, values = val)
                break

        return await interaction.channel.delete()
    
    @button(label = '重新開啟頻道', style=discord.ButtonStyle.green)
    async def reopen_callback(self, interaction:Interaction, button:Button):
        #get the customers of the channel
        now_channel = 0
        for index, channel in enumerate(self.main.channel_info):
            if channel[1] == interaction.channel:
                now_channel = self.main.channel_info[index]
                break
        #set the permissions
        for customer in now_channel[0]:
            try:
                perms = interaction.channel.overwrites_for(customer)
                perms.read_messages = True
                await interaction.channel.set_permissions(customer, overwrite = perms)
            except:
                pass
        await interaction.message.edit(view = None)
        return await interaction.response.send_message(
            '頻道已被重新開啟', 
            view = CloseToggle(main = self.main)
        )

class FeedBackSystem(View):
    def __init__(self):
        super().__init__(timeout = 86400)

    async def btns_callback(self, interaction:Interaction, button:Button):
        star = int(button.custom_id[:1])
        star_emoji = ''
        for i in range(star):
            star_emoji += '⭐'

        await interaction.message.edit(view = None)
        feed_back_channel = interaction.client.get_channel(feedback_channel)
        embed = await feed_back_embed_to_channel(interaction = interaction, button = button)
        msg = await interaction.user.send(f'評分 {star_emoji} 已傳送!感謝您的惠顧!')
        await msg.add_reaction('✅')
        
        await interaction.user.send('若您有興趣的話，請選擇想與今天服務人員說的話', view = words_selction())
        return await feed_back_channel.send(embed = embed)


    #先將回饋embed之類的東西灌進bot_info內
    @button(label = '⭐', style=discord.ButtonStyle.blurple, custom_id = '1star')
    async def one_star_callback(self, interaction:Interaction, button:Button):
        return await self.btns_callback(interaction = interaction, button = button)
    
    @button(label = '⭐⭐', style=discord.ButtonStyle.blurple, custom_id = '2star')
    async def two_star_callback(self, interaction:Interaction, button:Button):
        return await self.btns_callback(interaction = interaction, button = button)

    @button(label = '⭐⭐⭐', style=discord.ButtonStyle.blurple, custom_id = '3star')
    async def three_star_callback(self, interaction:Interaction, button:Button):
        return await self.btns_callback(interaction = interaction, button = button)

    @button(label = '⭐⭐⭐⭐', style=discord.ButtonStyle.blurple, custom_id = '4star')
    async def four_star_callback(self, interaction:Interaction, button:Button):
        return await self.btns_callback(interaction = interaction, button = button)

    @button(label = '⭐⭐⭐⭐⭐', style=discord.ButtonStyle.blurple, custom_id = '5star')
    async def five_star_callback(self, interaction:Interaction, button:Button):
        return await self.btns_callback(interaction = interaction, button = button)

class words_selction(View):
    def __init__(self):
        super().__init__(timeout = 86400)

    @select(            
        placeholder='請選擇評語',
        options=words_options,
        custom_id = 'review',
        min_values=1,
        max_values=len(words_options)
    )
    async def words_callback(self, interaction:Interaction, select:discord.ui.Select):
        return await review_words_embed(
            interaction = interaction,
            select = select
        )    

class channel(commands.Cog):
    def __init__(self, client, main:OpenButtons):
        self.main = main
        self.client = client

    async def if_in_channel(self, channel:discord.TextChannel):
        sql_cmd = 'SELECT * FROM customers'
        raw_data = MySqlDataBase.get_db_data(self = MySqlDataBase(), sql_cmd = sql_cmd)
        in_channel = False
        for cnl in raw_data:
            if cnl[1] == str(channel.id):
                in_channel = True

        return in_channel


    async def customer_management(self, channel:discord.TextChannel, args, add_or_remove:bool):
        #add_or_remove: True for add, False for remove
        if await self.if_in_channel(channel = channel):
            has_customer = False
            for member in channel.members:
                if args == str(member.id):
                    has_customer = True                
            
            if add_or_remove:
                if has_customer:
                    return await channel.send('此用戶已在頻道內!')
                else:
                    perms = channel.overwrites_for(self.client.get_user(int(args)))
                    perms.read_messages = True
                    await channel.set_permissions(self.client.get_user(int(args)), overwrite=perms)
                    channel_info = self.main.channel_info
                    for channels in channel_info:
                        if channels[1] == channel:
                            channels[0].append(self.client.get_user(int(args)))
                    self.main.channel_info = channel_info
                    return await channel.send(f'{self.client.get_user(int(args)).mention}已被加入頻道!')
            else:
                if not has_customer:
                    return await channel.send('此用戶不在頻道內!')
                else:
                    perms = channel.overwrites_for(self.client.get_user(int(args)))
                    perms.read_messages = True
                    await channel.set_permissions(self.client.get_user(int(args)), overwrite=perms)
                    channel_info = self.main.channel_info
                    for channels in channel_info:
                        if channels[1] == channel:
                            channels[0].remove(self.client.get_user(int(args)))
                    self.main.channel_info = channel_info
                    return await channel.send(f'{self.client.get_user(int(args)).mention}已被移出頻道!')
        else:
            msg = await channel.send(content = '這裡不是客服頻道!')
            return await msg.add_reaction('❗')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user:
            return
        else:
            if len(message.raw_mentions) == 0 and len(message.raw_role_mentions) == 0:
                if await self.if_in_channel(channel = message.channel):
                    if get_keyword_response(msg_content = message.content) != 0:
                        return await message.channel.send(get_keyword_response(msg_content = message.content))
                    else:
                        return
            else:
                mentioned = False
                for mentions in message.raw_mentions:
                    if mentions == 403844178687033345 or mentions == self.client.user.id or (not self.client.get_user(mentions).bot):
                        mentioned = True
                        break

                role_mentioned = False
                for mentions in message.raw_role_mentions:
                    if mentions == 856792148060667934 or mentions == 446617195049517056 or mentions == 584419521692172316:
                        role_mentioned = True
                        break

                if await self.if_in_channel(channel = message.channel) and (mentioned or role_mentioned):
                    await message.channel.send('你好！我們已收到你的訊息，感謝你與我們聯繫。待上線後將會回答您的問題~')
                elif (not await self.if_in_channel(channel = message.channel)) and self.client.user.mentioned_in(message):
                    await get_embed.help_embed(self = self, message = message, cmd = '0')
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if await self.if_in_channel(channel = before.channel):
            if len(after.raw_mentions) != 0:
                mentioned = False
                for x in after.raw_mentions:
                    if x == 403844178687033345 or x == self.client.user.id:
                        mentioned = True
                        break
                
                if mentioned:
                    await after.channel.send('你好！我們已收到你的訊息，感謝你與我們聯繫。待上線後將會回答您的問題~')

    @commands.command(name = 'purchase', aliases = ['New', 'new'])
    async def purchase(self, ctx):
        return await ctx.send(view = OpenButtons(client=self.client), content = the_msg(role = ctx.guild.get_role(cus_service_role_id), cmd_channel = self.client.get_channel(cmd_channel_id)), embed = get_embed.get_purchase_embed(self))

    @commands.command(name = 'close')
    async def close(self, ctx):
        if await self.if_in_channel(channel = ctx.channel):
            return await ctx.send(
                content = '新的關閉頻道按鈕:',
                view = CloseToggle(main = OpenButtons(client = self.client))
            )
        else:
            msg = await ctx.send(content = '這裡不是客服頻道!')
            return await msg.add_reaction('❗')

    @commands.command(name='save_channel', aliases =['save_cnl'])
    async def save_channel(self, ctx):
        if await self.if_in_channel(channel  = ctx.channel):
            channel = ctx.message.channel
            transcript = await chat_exporter.export(channel)
            transcript_file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"{channel.name}.html"
            )
            return await channel.send(file=transcript_file)
        else:
            msg = await ctx.send(content = '這裡不是客服頻道!')
            return await msg.add_reaction('❗')

    @commands.command(name = 'add_customer', aliases = ['add_cus'])
    async def add_customer(self, ctx, id):
        return await self.customer_management(channel = ctx.channel, args = id, add_or_remove = True)
    
    @commands.command(name = 'remove_customer', aliases = ['rm_cus'])
    async def remove_customer(self, ctx, id):
        return await self.customer_management(channel = ctx.channel, args = id, add_or_remove = False)
    
async def setup(client):
    await client.add_cog(channel(client = client, main = OpenButtons(client = client)))