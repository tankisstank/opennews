from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotifyConfig:
    enabled: bool = False
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    timeout_sec: int = 15


class NotifyAdapter:
    def __init__(self, config: NotifyConfig):
        self.config = config

    def send(self, text: str, payload: dict | None = None) -> None:
        if not self.config.enabled:
            return
        if self.config.telegram_enabled:
            self._send_telegram(text)
        if self.config.webhook_enabled:
            self._send_webhook(text, payload or {})

    def _send_telegram(self, text: str) -> None:
        token = self.config.telegram_bot_token
        chat_id = self.config.telegram_chat_id
        if not token or not chat_id:
            logger.warning("notify.telegram enabled but TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
                if resp.status >= 300:
                    logger.warning("telegram notify non-2xx: %s", resp.status)
        except Exception:
            logger.exception("telegram notify failed")

    def _send_webhook(self, text: str, payload: dict) -> None:
        url = self.config.webhook_url
        if not url:
            logger.warning("notify.webhook enabled but WEBHOOK_URL missing")
            return

        body = {
            "text": text,
            "payload": payload,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
                if resp.status >= 300:
                    logger.warning("webhook notify non-2xx: %s", resp.status)
        except Exception:
            logger.exception("webhook notify failed")
