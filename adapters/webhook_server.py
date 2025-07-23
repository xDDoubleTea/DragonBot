import hmac
import logging
from aiohttp import web
import json
import asyncio

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.ticket_service import TicketService
    
from models.ticket import NewTicketPayload

logger = logging.getLogger(__name__)

def setup_webhook_server(ticket_service: 'TicketService', shared_secret: str) -> web.Application:
    @web.middleware
    async def auth_middleware(request: web.Request, handler):
        if not shared_secret:
            logger.critical("[Security Error] Webhook 共享金鑰未在 .env 中設定！")
            return web.json_response({"error": "Bot's shared secret is not configured."}, status=500)

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return web.json_response({"error": "Missing or invalid Authorization header."}, status=401)

        token = auth_header.split(' ', 1)[1]
        if not hmac.compare_digest(token, shared_secret):
            logger.warning("無效的 Webhook 請求遭拒 (token不符)。")
            return web.json_response({"error": "Unauthorized."}, status=403)

        return await handler(request)

    async def handle_new_ticket(request: web.Request) -> web.Response:
        try:
            data = await request.json()
            payload = NewTicketPayload(**data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Webhook /ticket/create 收到無效的資料格式: {e}")
            return web.json_response({"error": "缺少或無效的必要資料"}, status=400)

        asyncio.create_task(ticket_service.create_ticket_from_webhook(payload))
        return web.json_response({"message": "頻道建立請求已接收，正在處理中"}, status=202)

    async def handle_new_reply(request: web.Request) -> web.Response:
        try:
            data = await request.json()
            ticket_id = int(data["ticket_id"])
            sender = str(data["sender"])
            message = str(data["message"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return web.json_response({"error": "缺少或無效的必要資料"}, status=400)

        asyncio.create_task(ticket_service.add_reply_from_webhook(ticket_id, sender, message))
        return web.json_response({"message": "回覆已接收"}, status=202)

    async def handle_close_ticket(request: web.Request) -> web.Response:
        try:
            data = await request.json()
            ticket_id = int(data["ticket_id"])
            closed_by = data.get("closed_by", "網站/客戶端")
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return web.json_response({"error": "ticket_id 缺失或格式錯誤"}, status=400)

        asyncio.create_task(ticket_service.close_ticket(ticket_id, closed_by))
        return web.json_response({"message": "關閉客服單請求已接收"}, status=202)

    app = web.Application(middlewares=[auth_middleware])
    app.add_routes([
        web.post('/ticket/create', handle_new_ticket),
        web.post('/ticket/update', handle_new_reply),
        web.post('/ticket/close', handle_close_ticket)
    ])
    return app