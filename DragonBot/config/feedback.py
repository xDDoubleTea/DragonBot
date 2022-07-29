import discord
import time
from datetime import date
from config.bot_info import *
import chat_exporter
import io

words_options = [
    discord.SelectOption(
        label = '服務速度快速',
        emoji='✅',
        default=False
    ),
    discord.SelectOption(
        label = '服務態度良好',
        emoji='✅',
        default=False
    ),
    discord.SelectOption(
        label = '服務優質',
        emoji='✅',
        default=False
    )
]

feedback_channel = 1

async def feedbackEmbed(channel:discord.TextChannel, client:discord.Client,customers:list, view:View):
    embed = discord.Embed(
        title='顧客意見調查表',
        description='調查顧客之意見使龍龍代購更好',
        color = discord.Color.from_rgb(190, 119, 255)
    )
    embed.add_field(name='剛剛的服務頻道', value=channel.name)
    t = time.localtime()
    today = date.today()
    today_date = today.strftime("%Y/%m/%d")
    current_time = time.strftime("%H:%M:%S", t)
    embed.set_author(name = f"{client.user}")
    embed.set_footer(text = f"{default_footer} \n {today_date} , {current_time}")
    for i in customers:
        if i != None:
            transcript = await chat_exporter.export(channel)
            transcript_file = discord.File(io.BytesIO(transcript.encode()),
                                       filename=f"{channel.name}.html")
            try:
                await i.send('此為對話記錄檔案:')
                await i.send(file=transcript_file)
                await i.send('說明:點選星數來代表今天服務的滿意度,而下拉式選單可選擇評語')
                return await i.send(embed=embed,view=view)
            except:
                return

async def feed_back_embed_to_channel(interaction:discord.Interaction, button:discord.ui.Button):
    embed = discord.Embed(
            title = '顧客回饋',
            description = "回饋單",
            colour = discord.Colour.from_rgb(190, 119, 255)
        )
    star = int(button.custom_id[:1])
    star_emoji = ''
    for i in range(star):
        star_emoji += '⭐'
    embed.add_field(name='顧客', value=interaction.user.mention, inline=True)
    embed.add_field(name='滿意度', value=star_emoji, inline = True)
    t = time.localtime()
    today = date.today()
    today_date = today.strftime("%Y/%m/%d")
    current_time = time.strftime("%H:%M:%S", t)
    embed.set_author(name = f"{interaction.client.user}")
    embed.set_footer(text = f"{default_footer} \n {today_date} , {current_time}")
    embed.set_thumbnail(url = 'https://i.imgur.com/AgKFvBT.png')
    return embed


async def review_words_embed(interaction:discord.Interaction, select:discord.ui.Select):
    await interaction.response.defer()
    await interaction.message.edit(view=None)
    data = interaction.data
    channel = await interaction.client.fetch_channel(feedback_channel)
    embed = discord.Embed(
        title = '顧客回饋',
        description = "回饋",
        colour = discord.Colour.from_rgb(190, 119, 255)
    )
    output = ""
    for index,value in enumerate(data["values"]):
        output += f'`{value}`'
        if index < len(data["values"])-1:
            output += '、'
    embed.add_field(name='顧客', value=interaction.user.mention, inline=True)
    embed.add_field(name='評語', value=f'{output}', inline = True)
    t = time.localtime()
    today = date.today()
    today_date = today.strftime("%Y/%m/%d")
    current_time = time.strftime("%H:%M:%S", t)
    embed.set_author(name = f"{interaction.client.user}")
    embed.set_footer(text = f"{default_footer} \n {today_date} , {current_time}")
    embed.set_thumbnail(url = 'https://i.imgur.com/AgKFvBT.png')
    await channel.send(embed = embed)
    msg = await interaction.user.send(f'評語{output}已傳送!感謝您的惠顧!')
    return await msg.add_reaction('✅')