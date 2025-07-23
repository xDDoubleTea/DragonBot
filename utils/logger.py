import logging
import sys
import config

import requests

class DiscordWebhookHandler(logging.Handler):
    """一個將日誌記錄發送到 Discord Webhook 的 Handler。"""
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        log_entry = self.format(record)
        payload = {"content": f"```log\n{log_entry}```"}
        headers = {"Content-Type": "application/json"}
        try:
            requests.post(self.webhook_url, json=payload, headers=headers, timeout=5)
        except Exception:
            pass

def setup_logging():
    """設定日誌格式與輸出目標。"""
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    
    logger = logging.getLogger()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if config.DISCORD_LOG_WEBHOOK_URL:
        discord_handler = DiscordWebhookHandler(config.DISCORD_LOG_WEBHOOK_URL)
        discord_handler.setLevel(logging.WARNING)
        discord_handler.setFormatter(formatter)
        logger.addHandler(discord_handler)