from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class NewsProcessedEvent:
    batch_id: int | None
    batch_ts: str
    news_id: str
    news_url: str | None = None
    title: str | None = None
    source: str | None = None
    published_at: str | None = None
    source_language: str | None = None
    result: str = "news processed successfully"
    completed_at: str = field(default_factory=utc_now_iso)
    channels_requested: tuple[str, ...] = ()
    preferred_language: str | None = None
    template_context: dict[str, Any] = field(default_factory=dict)
    localized_template_context: dict[str, Any] = field(default_factory=dict)

    def resolved_title(self) -> str:
        return self.title or self.news_id or "(untitled news)"

    def with_template_context(self) -> "NewsProcessedEvent":
        if self.template_context:
            return self
        self.template_context = {
            "batch_id": self.batch_id,
            "batch_ts": self.batch_ts,
            "news_id": self.news_id,
            "news_url": self.news_url,
            "title": self.resolved_title(),
            "source": self.source,
            "published_at": self.published_at,
            "result": self.result,
            "completed_at": self.completed_at,
        }
        return self

    def resolved_context(self) -> dict[str, Any]:
        return self.localized_template_context or self.template_context or self.with_template_context().template_context


@dataclass(slots=True)
class PipelineRunSummary:
    status: str
    result: str
    batch_id: int | None = None
    batch_ts: str | None = None
    record_count: int = 0
    news_events: list[NewsProcessedEvent] = field(default_factory=list)
    graph_status: str | None = None
    completed_at: str = field(default_factory=utc_now_iso)

    def should_notify(self) -> bool:
        return (
            self.status == "success"
            and self.batch_id is not None
            and self.record_count > 0
            and bool(self.news_events)
        )


@dataclass(slots=True)
class NotificationDeliveryAttempt:
    news_id: str
    sink_kind: str
    attempt_number: int
    status: str
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    sanitized_destination: str | None = None
    requested_language: str | None = None
    delivered_language: str | None = None
    translation_status: str | None = None
    fallback_reason: str | None = None


@dataclass(slots=True)
class NotificationDispatchSummary:
    attempts: list[NotificationDeliveryAttempt] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def delivered_count(self) -> int:
        return sum(1 for attempt in self.attempts if attempt.status == "success")
