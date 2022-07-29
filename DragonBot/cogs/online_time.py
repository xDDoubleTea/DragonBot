from msilib.schema import TextStyle
import discord
from discord.ext import commands
import math
from discord.ui import Button , View, Modal
import mysql.connector
import json

class btn(discord.ui.Button):
    async def callback(self ,interaction):
        if interaction.user.id == int(interaction.data['custom_id']):
            await interaction.response.send_modal(mymodal())
        else:
            await interaction.response.send_message('你不是這個指令的發起人!', ephemeral=True)


class mymodal(discord.ui.Modal, title='在線時間'):
    times = discord.ui.TextInput(label = '輸入區', style=discord.TextStyle.paragraph, placeholder='00:00~13:50\n00:00~22:30\n(以換行區隔，從星期一開始，一次填滿)', custom_id=f'time')

    async def on_submit(self, interaction):
        time_value = self.times.value
        start_time = []
        end_time = []
        for day in time_value.splitlines():
            start_time.append(day.split('~')[0])
            end_time.append(day.split('~')[1])


        with open('date_time.json', 'r') as file:
            date_time = json.load(file)


        index = 0
        for start, end in zip(start_time, end_time):
            index += 1
            date_time["date_data"][index-1].update({"date":index, "start_time":start, "end_time":end})

        with open('date_time.json', 'w') as file:
            json.dump(date_time, file, indent = 4)
        

        embed = discord.Embed(
            title = 'Date',
            description = '檢查在線時間',
            color = discord.Colour.from_rgb(190, 119, 255)
        )
        for i,x in enumerate(start_time):
            if i != 6:
                embed.add_field(name = f'星期{i+1}', value = f'{x}~{end_time[i]}', inline=False)
            else:
                embed.add_field(name = f'星期日', value = f'{x}~{end_time[i]}')
        
        await interaction.response.send_message(embed=embed,ephemeral=True)


class online_time(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.command(name = 'set_online')
    @commands.has_permissions(administrator = True)
    async def set_online(self, ctx):
        button = btn(
            style = discord.ButtonStyle.blurple,
            label = '設定在線時間',
            custom_id = f'{ctx.message.author.id}'
        )
        v = View(timeout=None)
        v.add_item(button)
        await ctx.channel.send(view=v)
    

    @commands.command(name = 'now_online')
    @commands.has_permissions(administrator = True)
    async def now_online(self, ctx):
        with open('date_time.json','r') as file:
            date_time = json.load(file)
        

        embed = discord.Embed(
            title = '營業時間',
            description = '檢查在線時間',
            color = discord.Colour.from_rgb(190, 119, 255)
        )
        for x in date_time["date_data"]:
            if x["date"] != 7:
                embed.add_field(name = f'星期{x["date"]}', value = f'{x["start_time"]}~{x["end_time"]}', inline=False)
            elif x["date"] == 7:
                embed.add_field(name = f'星期日', value = f'{x["start_time"]}~{x["end_time"]}', inline=False)


        await ctx.channel.send(embed=embed)


async def setup(client):
    await client.add_cog(online_time(client))