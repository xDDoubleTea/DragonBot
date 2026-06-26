from discord import Role, TextChannel, Color, Object
from dotenv import load_dotenv
import os

__all__ = [
    "bot_token",
    "pre",
    "eng_to_chinese",
    "CURRENCY_INFO_URL",
    "MY_USER_ID",
    "VERSION",
    "MY_DISCORD_ID",
    "DEFAULT_FOOTER",
    "cmd_channel_id",
    "cus_service_role_id",
    "THEME_COLOR",
    "logchannel_id",
    "archive_channel_id",
    "ericdragon_user_id",
    "feedback_channel_id",
    "app_id",
    "MY_GUILD",
    "DS01",
    "DISCORD_EMOJI",
    "ticket_system_main_message",
    "app_mode",
    "db_url",
    "admin_role_id",
    "epic_dragon_role_id",
    "rare_dragon_role_id",
    "exporter_bot_token",
]


load_dotenv()


def get_required_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        exit(f"{key} is not configured!")
    return val


app_mode = os.getenv("APP_MODE")

exporter_bot_token = get_required_env("EXPORTER_BOT_TOKEN")

assert app_mode in ["test", "prod"], "APP_MODE must be either 'test' or 'prod'"

app_mode = app_mode.lower()
db_url = (
    os.getenv("DATABASE_PROD_URL")
    if app_mode == "prod"
    else os.getenv("DATABASE_TEST_URL")
)
pre = os.getenv("PREFIX_PROD") if app_mode == "prod" else os.getenv("PREFIX_TEST")
bot_token = (
    get_required_env("BOT_TOKEN_PROD")
    if app_mode == "prod"
    else get_required_env("BOT_TOKEN_TEST")
)


eng_to_chinese = {
    "Monday": "一",
    "Tuesday": "二",
    "Wednesday": "三",
    "Thursday": "四",
    "Friday": "五",
    "Saturday": "六",
    "Sunday": "日",
}


MY_USER_ID = 398444155132575756
VERSION = 4.0
MY_DISCORD_ID = "hoshiyomi6942"
DEFAULT_FOOTER = f"Developed by {MY_DISCORD_ID} version:{VERSION}"


cmd_channel_id = 461556173011943435 if app_mode == "prod" else 1073168107813740556
# In production guild, cmd_channel_id is 461556173011943435
# In test guild, cmd_channel_id is 1073168107813740556

cus_service_role_id = 856792148060667934 if app_mode == "prod" else 1388896580173828188
# In production guild, cus_service_role_id is 856792148060667934
# In test guild, cus_service_role_id is 1388896580173828188

THEME_COLOR = Color.from_rgb(190, 119, 255)
ericdragon_user_id = 403844178687033345

admin_role_id = 740487435015946271
epic_dragon_role_id = 740487435015946271
rare_dragon_role_id = 446617194743201792

logchannel_id = 977445485180751882 if app_mode == "prod" else 1388896453446991902
# In production guild, logchannel is 977445485180751882
# In test guild, logchannel is 1388896453446991902

archive_channel_id = 1015983550782263356 if app_mode == "prod" else 1390385918816292895

app_id = 973570456076558406 if app_mode == "prod" else 865240620233785344
# In production guild, app_id is 973570456076558406
# In test guild, app_id is 865240620233785344

feedback_channel_id = 976831519995875338 if app_mode == "prod" else 1390873409143046225


MY_GUILD = (
    Object(id=1039906085626196079)
    if app_mode == "test"
    else Object(id=403844884374487040)
)
# guild dragon 403844884374487040
# test guild 1039906085626196079

CURRENCY_INFO_URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"

DS01 = "<:ds01:894967438733606943>"
DISCORD_EMOJI = "<:discord:934326257699663872>"


def ticket_system_main_message(role: Role, cmd_channel: TextChannel):
    return f"""
# ⭐ 客服開單系統 ⭐
> **請務必詳閱以下內容後，再開啟客服單為您服務**
## 1. 開單前請確認需求
- 請確認需求，有需要問問題或聯絡客服人員再開啟，**勿惡意或反覆開啟關閉**，違者將**警告懲處**。
## 2. 查詢訂單進度請先至網站
- 進入：[我的帳號 → 訂單](https://dragonshop.org/my-account/orders) 查看處理狀態。
- 若在**營業時間內**付款後 **1 小時仍未處理**，再開單並提供訂單編號即可。
## 3. 開啟私人頻道後請注意以下事項：
- 於開單時 **直接輸入詳細問題內容送出後等待回覆**，請勿洗版、重複Tag、持續追問，客服並非 24 小時盯著訊息。
- 我們將依照開單順序處理，如營業時間內 **30 分鐘內無回覆**，可 **Tag 一次** {role.mention}，感謝配合與耐心等待。
## 4. 問題解決後請**自行關閉客服頻道**：
- 若客服詢問後 **24 小時未回覆** 或用戶**自行關閉**，將由客服人員自動結案。
## 5. **請勿私訊或加好友詢問問題**：
- 我們**不會透過私訊回覆問題**，請使用龍龍代購提供的客服系統洽詢。
- **認明擁有**{role.mention}**身分組** 為官方客服人員。
## 6. 匯率參考
- **自定義代購匯率（美元、歐元）** 可先至 {cmd_channel.mention} 試算，詳細報價以客服人員回覆為準，勿自行下單。
## 7. 常見問題請先參閱 📚 [常見問答集FAQ](https://dragonshop.org/faq/)  若無法解決，歡迎開單詢問。
## ❔ 不知道要按哪個
有關代購類問題都點**代購** | 自定義代購報價詢問點**自定義代購** | 群組問題、領獎、檢舉騷擾...等點**群組**
```營業時間:
【平日】下午6點
【假日】中午12點-起至凌晨12點```
"""
