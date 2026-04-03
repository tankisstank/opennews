from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterable, Protocol
from urllib.parse import urlparse

from opennews.config import settings
from opennews.llm.client import LLMConfig
from opennews.notify.localization import LLMNotificationTranslator, LocalizationResult, NotificationLocalizer
from opennews.notify.models import (
    NewsProcessedEvent,
    NotificationDeliveryAttempt,
    NotificationDispatchSummary,
    PipelineRunSummary,
)
from opennews.notify.telegram import TelegramNotificationSink
from opennews.notify.webhook import WebhookNotificationSink

logger = logging.getLogger(__name__)


class NotificationSink(Protocol):
    kind: str
    destination: str

    def send(self, event: NewsProcessedEvent) -> None:
        ...


@dataclass(slots=True)
class NotificationPolicy:
    timeout_seconds: float
    max_attempts: int


class NotificationService:
    def __init__(
        self,
        *,
        sinks: Iterable[NotificationSink] | None = None,
        notifications_enabled: bool,
        sink_enabled: dict[str, bool],
        policy: NotificationPolicy,
        localizer: NotificationLocalizer | None = None,
    ) -> None:
        self._sinks = {sink.kind: sink for sink in (sinks or [])}
        self._notifications_enabled = notifications_enabled
        self._sink_enabled = sink_enabled
        self._policy = policy
        self._localizer = localizer or NotificationLocalizer()

    def dispatch_summary(self, summary: PipelineRunSummary) -> NotificationDispatchSummary:
        if not self._notifications_enabled:
            return NotificationDispatchSummary(skipped_reason="notifications_disabled")
        if not summary.should_notify():
            return NotificationDispatchSummary(skipped_reason="summary_not_eligible")

        active_sinks = {
            kind: sink
            for kind, sink in self._sinks.items()
            if self._sink_enabled.get(kind, False)
        }
        if not active_sinks:
            logger.info(
                "notification skipped: no registered sinks enabled (batch_id=%s, batch_ts=%s)",
                summary.batch_id,
                summary.batch_ts,
            )
            return NotificationDispatchSummary(skipped_reason="no_enabled_sinks")

        attempts: list[NotificationDeliveryAttempt] = []
        for event in summary.news_events:
            event.with_template_context()
            for kind, sink in active_sinks.items():
                localization = self._localizer.localize_event(
                    event,
                    target_language=getattr(sink, "preferred_language", None),
                    sink_kind=kind,
                )
                attempts.extend(self._deliver_with_retry(localization, kind, sink))
        logger.info(
            "notification dispatch summary: batch_id=%s batch_ts=%s total_events=%s total_attempts=%s delivered=%s failed=%s",
            summary.batch_id,
            summary.batch_ts,
            len(summary.news_events),
            len(attempts),
            sum(1 for attempt in attempts if attempt.status == "success"),
            sum(1 for attempt in attempts if attempt.status == "failed"),
        )
        return NotificationDispatchSummary(attempts=attempts)

    def _deliver_with_retry(
        self,
        localization: LocalizationResult,
        sink_kind: str,
        sink: NotificationSink,
    ) -> list[NotificationDeliveryAttempt]:
        attempts: list[NotificationDeliveryAttempt] = []
        event = localization.event
        sanitized_destination = self._sanitize_destination(getattr(sink, "destination", ""))
        fallback_reason = self._sanitize_error_message(localization.fallback_reason or "")
        for attempt_number in range(1, self._policy.max_attempts + 1):
            started = time.perf_counter()
            try:
                sink.send(event)
                latency_ms = int((time.perf_counter() - started) * 1000)
                attempt = NotificationDeliveryAttempt(
                    news_id=event.news_id,
                    sink_kind=sink_kind,
                    attempt_number=attempt_number,
                    status="success",
                    latency_ms=latency_ms,
                    sanitized_destination=sanitized_destination,
                    requested_language=localization.requested_language,
                    delivered_language=localization.delivered_language,
                    translation_status=localization.translation_status,
                    fallback_reason=fallback_reason or None,
                )
                self._log_attempt(event, attempt)
                attempts.append(attempt)
                break
            except Exception as exc:
                latency_ms = int((time.perf_counter() - started) * 1000)
                attempt = NotificationDeliveryAttempt(
                    news_id=event.news_id,
                    sink_kind=sink_kind,
                    attempt_number=attempt_number,
                    status="failed",
                    latency_ms=latency_ms,
                    error_code=type(exc).__name__,
                    error_message=self._sanitize_error_message(str(exc)),
                    sanitized_destination=sanitized_destination,
                    requested_language=localization.requested_language,
                    delivered_language=localization.delivered_language,
                    translation_status=localization.translation_status,
                    fallback_reason=fallback_reason or None,
                )
                self._log_attempt(event, attempt)
                attempts.append(attempt)
        return attempts

    def _log_attempt(
        self,
        event: NewsProcessedEvent,
        attempt: NotificationDeliveryAttempt,
    ) -> None:
        level = logging.INFO if attempt.status == "success" else logging.WARNING
        logger.log(
            level,
            "notification %s: batch_id=%s batch_ts=%s news_id=%s sink=%s attempt=%s latency_ms=%s destination=%s error_code=%s error_message=%s",
            attempt.status,
            event.batch_id,
            event.batch_ts,
            event.news_id,
            attempt.sink_kind,
            attempt.attempt_number,
            attempt.latency_ms,
            attempt.sanitized_destination,
            attempt.error_code,
            attempt.error_message,
        )
        logger.log(
            level,
            "notification language: news_id=%s sink=%s requested_language=%s delivered_language=%s translation_status=%s fallback_reason=%s",
            event.news_id,
            attempt.sink_kind,
            attempt.requested_language,
            attempt.delivered_language,
            attempt.translation_status,
            attempt.fallback_reason,
        )

    @staticmethod
    def _sanitize_destination(destination: str) -> str:
        if not destination:
            return "unset"
        if "://" in destination:
            parsed = urlparse(destination)
            netloc = parsed.netloc or "hidden"
            if "@" in netloc:
                netloc = netloc.split("@", 1)[-1]
            return f"{parsed.scheme}://{netloc}"
        if len(destination) <= 4:
            return "***"
        return f"{destination[:2]}***{destination[-2:]}"

    @staticmethod
    def _sanitize_error_message(message: str) -> str:
        if not message:
            return ""
        sanitized = message.replace("\r", " ").replace("\n", " ").strip()
        if "bearer " in sanitized.lower():
            parts = sanitized.split()
            rebuilt: list[str] = []
            skip_next = False
            for index, part in enumerate(parts):
                if skip_next:
                    skip_next = False
                    continue
                if part.lower() == "bearer" and index + 1 < len(parts):
                    rebuilt.extend([part, "***"])
                    skip_next = True
                else:
                    rebuilt.append(part)
            sanitized = " ".join(rebuilt)
        if len(sanitized) > 180:
            sanitized = sanitized[:177] + "..."
        return sanitized


def build_notification_service(
    sinks: Iterable[NotificationSink] | None = None,
) -> NotificationService:
    resolved_sinks = list(sinks or [])
    registered_kinds = {sink.kind for sink in resolved_sinks}
    if settings.telegram_notifications_enabled and "telegram" not in registered_kinds:
        resolved_sinks.append(
            TelegramNotificationSink(
                bot_token=settings.telegram_bot_token,
                chat_id=settings.telegram_chat_id,
                timeout_seconds=settings.notification_timeout_seconds,
                template_name=settings.telegram_template_name,
                preferred_language=settings.telegram_preferred_language,
            )
        )
    if settings.webhook_notifications_enabled and "webhook" not in registered_kinds:
        resolved_sinks.append(
            WebhookNotificationSink(
                url=settings.webhook_url,
                timeout_seconds=settings.notification_timeout_seconds,
                auth_header=settings.webhook_auth_header,
            )
        )
    return NotificationService(
        sinks=resolved_sinks,
        notifications_enabled=settings.notifications_enabled,
        sink_enabled={
            "telegram": settings.telegram_notifications_enabled,
            "webhook": settings.webhook_notifications_enabled,
        },
        policy=NotificationPolicy(
            timeout_seconds=settings.notification_timeout_seconds,
            max_attempts=max(1, settings.notification_max_attempts),
        ),
        localizer=build_notification_localizer(),
    )


def build_notification_localizer() -> NotificationLocalizer:
    if not settings.telegram_preferred_language:
        return NotificationLocalizer()

    llm_config = LLMConfig.load(settings.llm_config_path)
    translator = None
    if llm_config.api_key:
        translator = LLMNotificationTranslator(llm_config)
    return NotificationLocalizer(translator=translator)
