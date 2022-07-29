import discord
import time
from discord import Role, Interaction
from datetime import date
from config.Mysql_info import MySqlDataBase
from discord.ui import View
import json

bot_token = 'token'
pre = '$'

My_user_id = 1
version = 2.0
MyDiscordID = "星詠み#6942"
default_footer = f"Developed by {MyDiscordID} version:{version}"

cmd_channel_id = 1

cus_service_role_id = 1

theme_color = discord.Colour.from_rgb(190, 119, 255)

logchannel = 1

ds01 = 1
discord_emoji = 1


def the_msg(role, cmd_channel):
    return f'⭐客服開單系統⭐\n注意事項:\n1.有需要再開啟，如不小心按到請自行關閉，沒事亂開或反覆開啟關閉，一律警告懲罰\n2.訂單付款完畢可至網站 我的帳號-訂單 查看訂單處理狀態，如營業時間 1小時內尚未處理完畢再連絡客服並報上訂單編號\n3.打開後請直接說出您的問題，不用打招呼、等有人回答才問、刷頻、一直Tag，我們會依開單順序一一回答各位的問題，如營業時間30分鐘未回覆再Tag一遍 {role.mention}  \n4.如您的問題已解決，請自行關閉客服頻道，如客服人員詢問24小時未回覆，將由客服人員關閉\n6.請不要以 私訊、加好友 客服人員，我們不會在私訊回覆或接受邀請，有 {role.mention} 身分組才是我們的官方客服人員\n7.自訂義代購美元、歐元匯率轉換可至 {cmd_channel.mention} 進行試算，詳細以客服人員報價為準\n ```營業時間:每日下午一點至凌晨一點 如有異動會在公告通知 ```'

def open_cnl_msg(interaction:Interaction, cus_service_role:Role):
    with open('date_time.json', 'r') as file:
        date_time = json.load(file)
    
        embed = discord.Embed(
            title = 'Date',
            description = '檢查在線時間',
            color = discord.Colour.from_rgb(190, 119, 255)
        )
        for x in date_time["date_data"]:
            if x["date"] != 7:
                embed.add_field(name = f'星期{x["date"]}', value = f'{x["start_time"]}~{x["end_time"]}', inline=False)
            elif x["date"] == 7:
                embed.add_field(name = f'星期日', value = f'{x["start_time"]}~{x["end_time"]}', inline=False)

    return (f'{interaction.user.mention}Hi，有什麼需要服務的嗎~留下訊息後請等待{cus_service_role.mention}回應😊', embed)


class get_embed:
    def get_purchase_embed(self):
        embed = discord.Embed(
                    title = '【DRAGON龍龍】客服專區',
                    description= '請點下方按鈕開啟客服頻道，點擊後會開啟一個只有您跟客服人員才看的到的私人頻道，即可至開啟的頻道傳送訊息，謝謝您。',
                    color=theme_color,
                    url = 'https://dragonshop.org/'
                )
        embed.set_image(url = 'https://i.imgur.com/AgKFvBT.png')
        t = time.localtime()
        today = date.today()
        today_date = today.strftime("%Y/%m/%d")
        current_time = time.strftime("%H:%M:%S", t)
        dev = self.client.get_user(My_user_id)
        embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
        embed.set_footer(text = f"{default_footer} \n Sent at {today_date} , {current_time}", icon_url=dev.avatar.url)
        return embed

    async def help_embed(self, message:discord.Message ,cmd:str):
        all_cmds = ['usd', 'eur','New', 'scs', 'close','key','keyrm', 'keylist', 'U', 'E','keywordslist', 'add_cus', 'rm_cus','money', 'money_list','add_money','set_online','now_online', 'cpu','ram', 'game']
        main_cmds = ['usd','U', 'eur', 'E']
        channel_cmds = ['New', 'scs', 'close', 'add_cus', 'rm_cus']
        key_cmds = ['key','keyrm', 'keylist', 'keywordslist']
        money_cmds = ['money', 'money_list', 'add_money']
        online_cmds = ['set_online','now_online']
        monitor_cmds = ['cpu', 'ram']
        game_cmds = ['game']
        if cmd == '0':
            embed = discord.Embed(
                title = 'Help menu',
                description = f'輸入`{pre}help <指令>`來查看指令使用方式!',
                color = discord.Colour.from_rgb(190, 119, 255)
            )
            
            embed.add_field(name='主要指令', value=f'`{", ".join(i for i in main_cmds)}`', inline=False)
            embed.add_field(name='創建頻道指令', value=f'`{", ".join(i for i in channel_cmds)}`', inline= False)
            embed.add_field(name='關鍵字指令', value=f'`{", ".join(i for i in key_cmds)}`', inline=False)
            embed.add_field(name='金錢系統', value=f'`{", ".join(i for i in money_cmds)}`', inline= False)
            embed.add_field(name='營業時間設置系統', value=f'`{", ".join(i for i in online_cmds)}`', inline=False)
            embed.add_field(name='機器人資源使用監控系統', value=f'`{", ".join(i for i in monitor_cmds)}`',inline=False)
            embed.add_field(name='遊戲指令', value = f'`{", ".join(i for i in game_cmds)}`', inline = False)
            t = time.localtime()
            today = date.today()
            today_date = today.strftime("%Y/%m/%d")
            current_time = time.strftime("%H:%M:%S", t)
            dev = self.client.get_user(My_user_id)
            embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
            embed.set_footer(text = f"{default_footer} \n Sent at {today_date} , {current_time}", icon_url=dev.avatar.url)
            v = View()
            btn = discord.ui.Button(
                style = discord.ButtonStyle.link,
                url = 'https://sites.google.com/whsh.tc.edu.tw/dragonbot/%E9%A6%96%E9%A0%81',
                disabled=False,
                label='此網站還在開發中'
            )
            v.add_item(btn)
            return await message.channel.send(embed = embed, view = v)
        elif cmd != '0':
            has_cmd = False
            for x in all_cmds:
                if x == cmd:
                    has_cmd = True
                    break
            if has_cmd:
                await message.channel.send('備註:<option>=必要參數,[option]=非必要參數')
                if cmd == 'usd' or cmd == 'U':
                    await message.channel.send(f'使用方法`{pre}usd <價錢>` or `{pre}U <價錢>`\n將回傳`NTD{pre}<價錢*30>`')
                elif cmd == 'eur' or cmd == 'E':
                    await message.channel.send(f'使用方法`{pre}eur <價錢>` or `{pre}E <價錢>`\n將回傳`NTD{pre}<價錢*35>`')
                elif cmd == 'New' or cmd == 'purchase':
                    await message.channel.send(f'使用方法`{pre}New` or `{pre}purchase`\n將回傳客服開單按鈕訊息')
                elif cmd == 'close':
                    await message.channel.send(f'<需管理員權限>使用方法`在客服頻道中輸入{pre}close`\n將回傳一`關閉頻道`按鈕')
                elif cmd == 'key':
                    await message.channel.send(f'<需管理員權限>使用方法`{pre}key <關鍵字> <回應>`\n若創建成功，回傳「<關鍵字>已加入資料庫」。\n若資料庫中已經有此關鍵字，則回傳「<關鍵字>已在資料庫中，是否做更動?」。\n關鍵字只有在客服頻道中被偵測到，才會觸發回覆功能，且只能偵測是否為關鍵字開頭的語句')
                elif cmd == 'keyrm':
                    await message.channel.send(f'<需管理員權限>使用方法`{pre}keyrm <關鍵字>`\n若移除成功，則回傳「<關鍵字>移除成功!」\n若無關鍵字，則回傳「未找到關鍵字!，使用{pre}keywordlist或{pre}keylist來得知目前資料庫中之關鍵字!」')
                elif cmd == 'keylist' or cmd == 'keywordlist':
                    await message.channel.send(f'使用方法`{pre}keylist [傳送方式]`\n將回傳所有在資料庫中的關鍵字\n傳送方式1表示在當前輸入指令之頻道傳送,傳送方式2表示在私訊中傳送')
                elif cmd == 'add_cus':
                    await message.channel.send(f'<需管理員權限>使用方法`{pre}add_cus <使用者ID> [客服頻道ID]`\n若使用者已在觸發指令之客服頻道(若於非客服頻道觸發且無提供頻道ID則回傳：此頻道非客服頻道)或提供之客服頻道，將回傳(使用者)已在客服頻道內，反則回傳已將(使用者)加入客服頻道內。\n若觸發指令之頻道(若於非客服頻道觸發且無提供頻道ID則回傳：此頻道非客服頻道)或提供之頻道不存在，則回傳頻道不存在。若未提供使用者ID，則回傳使用方法。')
                elif cmd == 'rm_cus':
                    await message.channel.send(f'<需管理員權限>使用方法`{pre}rm_cus <使用者ID> [客服頻道ID]`\n若使用者不在觸發指令之客服頻道(若於非客服頻道觸發且無提供頻道ID則回傳：此頻道非客服頻道)或提供之客服頻道，將回傳(使用者)不在客服頻道內，反則回傳已將(使用者)從客服頻道移除。\n若觸發指令之頻道(若於非客服頻道觸發且無提供頻道ID則回傳：此頻道非客服頻道)或提供之頻道不存在，則回傳頻道不存在。若未提供使用者ID，則回傳使用方法。')
                elif cmd == 'add_money':
                    await message.channel.send(f'<需管理員權限>使用方法`{pre}add_money <使用者ID> <金錢數量>`若要扣款直接打入負值')
                elif cmd == 'money_list':
                    await message.channel.send(f'使用方法:{pre}money_list，將回傳金錢排行榜')
                elif cmd == 'money':
                    await message.channel.send(f'使用方法:{pre}money [使用者ID]，若未填使用者id則回傳觸發指令使用者之金錢，若有填則回傳使用者id之擁有者之金錢')
                elif cmd == 'set_online':
                    await message.channel.send(f'<需管理員權限>使用方法`{pre}set_online`，將傳送一按鈕(只有觸發指令的人能按)，按下後會有彈出式視窗，可設置營業時間')
                elif cmd == 'now_online':
                    await message.channel.send(f'使用方法`{pre}now_online`，將回傳目前設置的營業時間')
                elif cmd == 'cpu':
                    await message.channel.send(f'使用方法`{pre}cpu`，將回傳目前CPU使用率(測試時間2秒)')
                elif cmd == 'ram':
                    await message.channel.send(f'使用方法`{pre}ram`，將回傳目前機器人佔用記憶體')
            else:
                await message.channel.send('未找到指令!以下是可使用的指令:')
                embed = discord.Embed(
                    title = 'Help menu',
                    description = f'輸入`{pre}help <指令>`來查看指令使用方式!',
                    color = discord.Colour.from_rgb(190, 119, 255)
                )
                embed.add_field(name='主要指令', value=f'`{", ".join(i for i in main_cmds)}`', inline=False)
                embed.add_field(name='創建頻道指令', value=f'`{", ".join(i for i in channel_cmds)}`', inline= False)
                embed.add_field(name='關鍵字指令', value=f'`{", ".join(i for i in key_cmds)}`', inline=False)
                embed.add_field(name='金錢系統', value=f'`{", ".join(i for i in money_cmds)}`', inline= False)
                embed.add_field(name='營業時間設置系統', value=f'`{", ".join(i for i in online_cmds)}`', inline=False)
                embed.add_field(name='機器人資源使用監控系統', value=f'`{", ".join(i for i in monitor_cmds)}`',inline=False)
                t = time.localtime()
                today = date.today()
                today_date = today.strftime("%Y/%m/%d")
                current_time = time.strftime("%H:%M:%S", t)
                dev = self.client.get_user(My_user_id)
                embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
                embed.set_footer(text = f"{default_footer} \n Sent at {today_date} , {current_time}", icon_url=dev.avatar.url)
                return await message.channel.send(embed = embed)
    async def send_bug_embed(self, ctx, bug_id, data):
        embed = discord.Embed(
            title='BUG回報',
            description='回報單給開發者',
            color=discord.Color.from_rgb(190, 112, 255)
        )
        embed.add_field(name='Bug敘述',value=data)
        t = time.localtime()
        today = date.today()
        today_date = today.strftime("%Y/%m/%d")
        current_time = time.strftime("%H:%M:%S", t)
        dev = self.client.get_user(My_user_id)
        embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
        embed.set_footer(text = f"{default_footer} \n Sent at {today_date} , {current_time}", icon_url=dev.avatar.url)
        await ctx.channel.send(embed = embed)
        logs_channel = self.client.get_channel(logchannel)
        bug_embed = discord.Embed(
            title = 'BUG REPORT',
            description='This is a BUG REPORT',
            color=discord.Color.from_rgb(190,112,255)
        )
        bug_embed.add_field(name='BUG Desc', value=data, inline=False)
        bug_id += 1
        bug_embed.add_field(name='BUG id', value=bug_id,inline=True)
        bug_embed.add_field(name='Report by', value=ctx.message.author.mention)
        bug_embed.add_field(name='Status', value='NOT YET')
        dev = self.client.get_user(My_user_id)
        bug_embed.set_author(name = f"{self.client.user}", icon_url=self.client.user.avatar.url)
        bug_embed.set_footer(text = f"{default_footer} \n Sent at {today_date} , {current_time}", icon_url=dev.avatar.url)
        

        with open('bug_id.json','w') as file:
            json.dump({"bug_id":bug_id}, file , indent = 4)
        return await logs_channel.send(content = bug_id, embed=bug_embed)

def get_keyword_response(msg_content:str):
    sql_cmd = 'SELECT * FROM keyword'
    keywords = MySqlDataBase.get_db_data(self = MySqlDataBase(), sql_cmd = sql_cmd)
    has_keyword = False
    response = ''
    for word in keywords:
        if msg_content.startswith(word[0]):
            has_keyword = True
            response = word[1]
            break
    if has_keyword:
        return response
    else:
        return 0
            