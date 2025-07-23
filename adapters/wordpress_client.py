import logging
from typing import Optional, Dict, Any

import aiohttp

from models.ticket import OrderDetails

logger = logging.getLogger(__name__)


class WordPressClient:
    """用於與 DragonShop WordPress API 互動的非同步客戶端。"""

    def __init__(self, api_url: str, api_key: str):
        if not api_key:
            logger.warning(
                "[Security Warning] WordPress API 金鑰 (DRAGONSHOP_API_SECRET_KEY) 未設定！"
            )
        self.base_url = f"{api_url}/wp-json/dragonshop/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def _request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """通用的非同步請求方法。"""
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession(
                headers=self.headers, timeout=self.timeout
            ) as session:
                async with session.request(method, url, **kwargs) as response:
                    if response.status in range(200, 300):
                        if response.status == 204:
                            return {"success": True}
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"WordPress API 請求失敗 ({method} {url}): "
                            f"狀態碼 {response.status}, 回應: {error_text}"
                        )
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"與 WordPress API 通訊時發生網路錯誤: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"處理 WordPress API 請求時發生未知錯誤: {e}", exc_info=True)
            return None

    async def update_ticket_message(
        self, ticket_id: int, sender: str, message: str
    ) -> bool:
        """更新客服單的對話內容。"""
        payload = {"ticket_id": ticket_id, "sender": sender, "message": message}
        result = await self._request("POST", "/ticket/update", json=payload)
        return result is not None

    async def close_ticket(self, ticket_id: int) -> bool:
        """將 WordPress 上的客服單狀態更新為 'closed'。"""
        payload = {"ticket_id": ticket_id}
        result = await self._request("POST", "/ticket/close", json=payload)
        return result is not None

    async def get_order_details(self, ticket_id: int) -> Optional[OrderDetails]:
        """根據 ticket_id 獲取訂單詳細資訊。"""
        params = {"ticket_id": ticket_id}
        data = await self._request("GET", "/order/details", params=params)
        if data:
            defined_fields = OrderDetails.__annotations__.keys()
            filtered_data = {
                key: value for key, value in data.items() if key in defined_fields
            }

            return OrderDetails(ticket_id=ticket_id, **filtered_data)
        return None

    # async def get_open_tickets(self) -> list[dict]:
    #     """獲取所有狀態為 'open' 的客服單。"""
    #     data = await self._request("GET", "/tickets/open")
    #     return data if data else []

    async def get_ticket_details(self, ticket_id: int) -> Optional[Dict]:
        """呼叫 /ticket/get 取得客服單的標題和對話紀錄。"""
        params = {"ticket_id": ticket_id}
        return await self._request("GET", "/ticket/get", params=params)

    async def get_channel_name(self, ticket_id: int) -> Optional[str]:
        """呼叫 /ticket/channel_name 取得原始頻道名稱。"""
        params = {"ticket_id": ticket_id}
        data = await self._request("GET", "/ticket/channel_name", params=params)
        return data.get("channel_name") if data else None
