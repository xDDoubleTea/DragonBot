from dataclasses import dataclass
from enum import Enum


@dataclass
class CannedResponse:
    text: str
    mention_user: bool = False


class ReplyKeys(Enum):
    CLOSE_PROMPT = "(@顧客) 如暫時沒其他需要服務的地方再幫我們關閉客服頻道喔~"
    PAYMENT = "(@顧客) 付款後通常營業時間一小時會完成訂單！如超過1小時未拿到(訂單狀態還在處理中)..."
    DONE_PROCESS = "(@顧客) 您的訂單已處理完畢，感謝您的購買與支持!"
    SERVICE_PROMPT = "(@顧客) 有什麼需要服務的地方請直接提出~"
    ORDER_GUIDE = "(@顧客) 自定義代購 請提供您要購買的商品連結(如手遊、app就是app名稱、登入方式)、購買/付款方式、價格(商品原本之價格)，如可以代購會報價給您"
    REQUEST_ORDER_ID = "(@顧客) 請提供訂單編號喔(#五碼)"
    RANK_PICKUP_INFO = "(@顧客) Rank要跟我們約時間上線領取喔~"
    FAQ_LINK = "常見問題Q&A: https://dragonshop.org/faq/"
    WEBSITE_LINK = "官網: https://dragonshop.org/"
    CUSTOM_ORDER_LINK = "自定義代購: https://dragonshop.org/product/%E8%87%AA%E5%AE%9A%E7%BE%A9%E4%BB%A3%E8%B3%BC/"
    PAYMENT_TUTORIAL = "超商付款教學: https://dragonshop.org/convenience-store/"


CANNED_RESPONSES: dict[ReplyKeys, CannedResponse] = {
    ReplyKeys.CLOSE_PROMPT: CannedResponse(
        text="如暫時沒其他需要服務的地方再幫我們關閉客服頻道喔~", mention_user=True
    ),
    ReplyKeys.PAYMENT: CannedResponse(
        text="付款後通常營業時間一小時會完成訂單！如超過1小時未拿到(訂單狀態還在處理中)請提供我們訂單編號或顧客資訊，要詢問訂單問題也請提供我們訂單編號(#五碼)\n一般問題可先參考常見問題Q&A: https://dragonshop.org/faq/",
        mention_user=True,
    ),
    ReplyKeys.DONE_PROCESS: CannedResponse(
        text="您的訂單已處理完畢，感謝您的購買與支持!", mention_user=True
    ),
    ReplyKeys.SERVICE_PROMPT: CannedResponse(
        text="有什麼需要服務的地方請直接提出~", mention_user=True
    ),
    ReplyKeys.ORDER_GUIDE: CannedResponse(
        text="自定義代購 請提供您要購買的商品連結(如手遊、app就是app名稱、登入方式)、購買/付款方式、價格(商品原本之價格)，如可以代購會報價給您",
        mention_user=True,
    ),
    ReplyKeys.REQUEST_ORDER_ID: CannedResponse(
        text="請提供訂單編號喔(#五碼)", mention_user=True
    ),
    ReplyKeys.RANK_PICKUP_INFO: CannedResponse(
        text="Rank要跟我們約時間上線領取喔~", mention_user=True
    ),
    ReplyKeys.FAQ_LINK: CannedResponse(text="常見問題Q&A: https://dragonshop.org/faq/"),
    ReplyKeys.WEBSITE_LINK: CannedResponse(text="官網: https://dragonshop.org/"),
    ReplyKeys.CUSTOM_ORDER_LINK: CannedResponse(
        text="自定義代購: https://dragonshop.org/product/%E8%87%AA%E5%AE%9A%E7%BE%A9%E4%BB%A3%E8%B3%BC/"
    ),
    ReplyKeys.PAYMENT_TUTORIAL: CannedResponse(
        text="超商付款教學: https://dragonshop.org/convenience-store/"
    ),
}
