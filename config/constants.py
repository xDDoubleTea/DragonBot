from discord import Role, TextChannel, Color, Object
from dotenv import load_dotenv
import os

__all__ = [
    "bot_token",
    "pre",
    "num_to_chinese",
    "My_user_id",
    "version",
    "MyDiscordID",
    "default_footer",
    "cmd_channel_id",
    "cus_service_role_id",
    "THEME_COLOR",
    "logchannel",
    "app_id",
    "MY_GUILD",
    "NOT_REQUESTABLE_ROLES_ID",
    "DS01",
    "DISCORD_EMOJI",
    "ticket_system_main_message",
    "app_mode",
    "db_url",
    "all_cmds",
    "channel_cmds",
    "key_cmds",
    "money_cmds",
    "online_cmds",
    "monitor_cmds",
    "game_cmds",
]
load_dotenv()
app_mode = os.getenv("APP_MODE")
assert app_mode in ["test", "prod"], "APP_MODE must be either 'test' or 'prod'"
app_mode = app_mode.lower()
db_url = (
    os.getenv("DATABASE_PROD_URL")
    if app_mode == "prod"
    else os.getenv("DATABASE_TEST_URL")
)
pre = os.getenv("PREFIX_PROD") if app_mode == "prod" else os.getenv("PREFIX_TEST")
bot_token = (
    os.getenv("BOT_TOKEN_PROD") if app_mode == "prod" else os.getenv("BOT_TOKEN_TEST")
)


num_to_chinese = ["一", "二", "三", "四", "五", "六", "日"]
My_user_id = 398444155132575756
version = 4.0
MyDiscordID = "hoshiyomi6942"
default_footer = f"Developed by {MyDiscordID} version:{version}"

cmd_channel_id = 461556173011943435 if app_mode == "prod" else 1073168107813740556
# In production guild, cmd_channel_id is 461556173011943435
# In test guild, cmd_channel_id is 1073168107813740556

cus_service_role_id = 856792148060667934 if app_mode == "prod" else 1388896580173828188
# In production guild, cus_service_role_id is 856792148060667934
# In test guild, cus_service_role_id is 1388896580173828188

THEME_COLOR = Color.from_rgb(190, 119, 255)

logchannel = 977445485180751882 if app_mode == "prod" else 1388896453446991902
# In production guild, logchannel is 977445485180751882
# In test guild, logchannel is 1388896453446991902


app_id = 973570456076558406 if app_mode == "prod" else 865240620233785344
# In production guild, app_id is 973570456076558406
# In test guild, app_id is 865240620233785344

MY_GUILD = (
    Object(id=1039906085626196079)
    if app_mode == "test"
    else Object(id=403844884374487040)
)
# guild dragon 403844884374487040
# test guild 1039906085626196079

NOT_REQUESTABLE_ROLES_ID = [
    584419521692172316,
    446617195049517056,
    740487435015946271,
    460120371476037633,
    446617194743201792,
    856792148060667934,
]

DS01 = "<:ds01:894967438733606943>"
DISCORD_EMOJI = "<:discord:934326257699663872>"


def ticket_system_main_message(role: Role, cmd_channel: TextChannel):
    return f"""
⭐客服開單系統⭐
請務必閱讀以下注意事項後再開啟:
1.有需要問問題或聯絡客服人員再開啟，如不小心按到請自行關閉，沒事亂開或反覆開啟關閉，一律警告懲處
2.訂單付款完畢可至網站 我的帳號-訂單 查看訂單處理狀態，如營業時間內 1小時尚未處理完畢再聯絡客服並報上訂單編號就好
3.開啟私人頻道後請直接詳細說出您的問題，不用打招呼或等有人回答才問，也請不要刷頻、\
一直Tag或問號，客服人員非一直盯著訊息看，我們人在時會依開單順序一一回答各位的問題，如營業時間內每30分鐘未回覆再Tag一遍 {role.mention} \
，感謝您的配合
4.如您的問題已解決，請自行點擊按鈕關閉客服頻道，如客服人員詢問24小時未回覆或自行關閉，將由客服人員關閉
6.請不要 私訊、加客服好友 問問題，我們不會在私訊回覆問題!請利用本客服系統開啟的私人頻道，並請認明有 {role.mention}\
身分組才是我們的官方客服人員
7.自定義代購美元、歐元匯率轉換可先至 {cmd_channel.mention}
進行試算參考，詳細以客服人員報價為準
{DS01}一般問題麻煩先參閱 常見問答集FAQ: https://dragonshop.org/faq/ 無法解答再開單{DS01}
```營業時間:\n【暑期】每日下午1點至晚上12點
如有臨時異動會在公告通知```
    """


all_cmds = [
    "New",
    "scs",
    "close",
    "key",
    "keyrm",
    "keylist",
    "keywordslist",
    "add_cus",
    "rm_cus",
    "money",
    "money_list",
    "add_money",
    "set_online",
    "now_online",
    "cpu",
    "ram",
    "game",
]
channel_cmds = ["New", "scs", "close", "add_cus", "rm_cus", "set_cnl_close"]
key_cmds = ["key", "keyrm", "keylist", "keywordslist"]
money_cmds = ["money", "money_list", "add_money"]
online_cmds = ["set_online", "now_online"]
monitor_cmds = ["cpu", "ram"]
game_cmds = ["game"]
