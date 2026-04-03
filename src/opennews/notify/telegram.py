from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import requests

from opennews.notify.models import NewsProcessedEvent


DEFAULT_TEMPLATE = """OpenNews processed a news item
Batch ID: {batch_id}
Batch TS: {batch_ts}
News ID: {news_id}
Title: {title}
Source: {source}
Result: {result}"""

VI_TEMPLATE = """OpenNews vừa xử lý xong một tin
Mã batch: {batch_id}
Thời điểm batch: {batch_ts}
Mã tin: {news_id}
Tiêu đề: {title}
Nguồn: {source}
Kết quả: {result}"""


def render_telegram_message(
    event: NewsProcessedEvent,
    *,
    template_name: str = "default",
) -> str:
    event.with_template_context()
    context_source = event.resolved_context()
    language = (event.preferred_language or "").lower()
    templates: dict[str, str] = {
        "default": DEFAULT_TEMPLATE,
    }
    if template_name not in templates:
        raise ValueError(f"unknown telegram template: {template_name}")
    context = {
        "batch_id": context_source.get("batch_id") or "-",
        "batch_ts": context_source.get("batch_ts") or "-",
        "news_id": context_source.get("news_id") or "-",
        "title": context_source.get("title") or "(untitled news)",
        "source": context_source.get("source") or "-",
        "result": context_source.get("result") or event.result,
    }
    template = VI_TEMPLATE if language.startswith("vi") else templates[template_name]
    return template.format_map(context)


@dataclass(slots=True)
class TelegramNotificationSink:
    bot_token: str
    chat_id: str
    timeout_seconds: float
    template_name: str = "default"
    preferred_language: str = ""
    sender: Callable[..., requests.Response] | None = None

    kind: str = "telegram"

    def __post_init__(self) -> None:
        if self.sender is None:
            self.sender = requests.post

    @property
    def destination(self) -> str:
        return self.chat_id

    def send(self, event: NewsProcessedEvent) -> None:
        if not self.bot_token:
            raise ValueError("telegram bot token is not configured")
        if not self.chat_id:
            raise ValueError("telegram chat id is not configured")

        response = self.sender(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text": render_telegram_message(event, template_name=self.template_name),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
