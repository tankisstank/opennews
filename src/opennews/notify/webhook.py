from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import requests

from opennews.notify.models import NewsProcessedEvent


def build_webhook_payload(event: NewsProcessedEvent) -> dict[str, Any]:
    event.with_template_context()
    return {
        "event_type": "news_processed",
        "batch": {
            "id": event.batch_id,
            "timestamp": event.batch_ts,
        },
        "news": {
            "id": event.news_id,
            "title": event.template_context.get("title") or event.resolved_title(),
            "source": event.source,
            "url": event.news_url,
            "published_at": event.published_at,
        },
        "result": {
            "status": "success",
            "summary": event.result,
        },
        "meta": {
            "completed_at": event.completed_at,
            "source": "opennews",
        },
    }


@dataclass(slots=True)
class WebhookNotificationSink:
    url: str
    timeout_seconds: float
    auth_header: str = ""
    sender: Callable[..., requests.Response] | None = None

    kind: str = "webhook"

    def __post_init__(self) -> None:
        if self.sender is None:
            self.sender = requests.post

    @property
    def destination(self) -> str:
        return self.url

    def send(self, event: NewsProcessedEvent) -> None:
        if not self.url:
            raise ValueError("webhook url is not configured")

        headers = {"Content-Type": "application/json"}
        if self.auth_header:
            name, value = self._parse_auth_header(self.auth_header)
            headers[name] = value

        response = self.sender(
            self.url,
            json=build_webhook_payload(event),
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

    @staticmethod
    def _parse_auth_header(raw_header: str) -> tuple[str, str]:
        if ":" not in raw_header:
            raise ValueError("webhook auth header must use 'Header-Name: value' format")
        name, value = raw_header.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            raise ValueError("webhook auth header is incomplete")
        return name, value
