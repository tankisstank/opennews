from __future__ import annotations

import unittest
from unittest.mock import patch

from opennews.notify.models import NewsProcessedEvent, PipelineRunSummary
from opennews.notify.localization import NotificationLocalizer
from opennews.notify.service import NotificationPolicy, NotificationService


class FakeSink:
    def __init__(self, kind: str, destination: str, *, fail: bool = False) -> None:
        self.kind = kind
        self.destination = destination
        self.fail = fail
        self.sent_news_ids: list[str] = []
        self.sent_events: list[NewsProcessedEvent] = []

    def send(self, event: NewsProcessedEvent) -> None:
        self.sent_news_ids.append(event.news_id)
        self.sent_events.append(event)
        if self.fail:
            raise RuntimeError(f"{self.kind} delivery failed")


class FakeTranslator:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str | None, str, dict[str, str]]] = []

    def translate_fields(
        self,
        fields: dict[str, str],
        *,
        target_language: str,
        source_language: str | None = None,
    ) -> dict[str, str]:
        self.calls.append((source_language, target_language, dict(fields)))
        if self.fail:
            raise RuntimeError("translation backend timed out")
        return {
            key: f"[{target_language}] {value}"
            for key, value in fields.items()
        }


def build_event(news_id: str, *, title: str | None = None) -> NewsProcessedEvent:
    return NewsProcessedEvent(
        batch_id=123,
        batch_ts="20260402_101500_123",
        news_id=news_id,
        title=title,
        source="seed",
        source_language="en-US",
        completed_at="2026-04-02T10:15:30+00:00",
    ).with_template_context()


class NotificationServiceTests(unittest.TestCase):
    def test_event_helper_populates_template_context_with_title_fallback(self) -> None:
        event = build_event("news-1", title=None)

        self.assertEqual(event.resolved_title(), "news-1")
        self.assertEqual(event.template_context["news_id"], "news-1")
        self.assertEqual(event.template_context["title"], "news-1")

    def test_dispatch_fans_out_each_event_to_each_enabled_sink(self) -> None:
        telegram = FakeSink("telegram", "chat-01")
        webhook = FakeSink("webhook", "https://example.com/hook")
        service = NotificationService(
            sinks=[telegram, webhook],
            notifications_enabled=True,
            sink_enabled={"telegram": True, "webhook": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
        )
        summary = PipelineRunSummary(
            status="success",
            result="updated 2 news into graph",
            batch_id=123,
            batch_ts="20260402_101500_123",
            record_count=2,
            news_events=[build_event("news-1"), build_event("news-2")],
        )

        dispatch_summary = service.dispatch_summary(summary)

        self.assertIsNone(dispatch_summary.skipped_reason)
        self.assertEqual(dispatch_summary.total_attempts, 4)
        self.assertEqual(dispatch_summary.delivered_count, 4)
        self.assertEqual(telegram.sent_news_ids, ["news-1", "news-2"])
        self.assertEqual(webhook.sent_news_ids, ["news-1", "news-2"])

    def test_dispatch_isolates_failures_per_sink(self) -> None:
        telegram = FakeSink("telegram", "chat-01")
        webhook = FakeSink("webhook", "https://example.com/hook", fail=True)
        service = NotificationService(
            sinks=[telegram, webhook],
            notifications_enabled=True,
            sink_enabled={"telegram": True, "webhook": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=2),
        )
        summary = PipelineRunSummary(
            status="success",
            result="updated 1 news into graph",
            batch_id=123,
            batch_ts="20260402_101500_123",
            record_count=1,
            news_events=[build_event("news-1", title="Hello")],
        )

        dispatch_summary = service.dispatch_summary(summary)

        self.assertEqual(dispatch_summary.total_attempts, 3)
        self.assertEqual(dispatch_summary.delivered_count, 1)
        self.assertEqual(telegram.sent_news_ids, ["news-1"])
        self.assertEqual(webhook.sent_news_ids, ["news-1", "news-1"])
        failed_attempts = [a for a in dispatch_summary.attempts if a.status == "failed"]
        self.assertEqual(len(failed_attempts), 2)

    def test_dispatch_localizes_telegram_only_when_preferred_language_is_configured(self) -> None:
        telegram = FakeSink("telegram", "chat-01")
        webhook = FakeSink("webhook", "https://example.com/hook")
        translator = FakeTranslator()
        service = NotificationService(
            sinks=[telegram, webhook],
            notifications_enabled=True,
            sink_enabled={"telegram": True, "webhook": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
            localizer=NotificationLocalizer(translator=translator),
        )
        summary = PipelineRunSummary(
            status="success",
            result="updated 1 news into graph",
            batch_id=123,
            batch_ts="20260402_101500_123",
            record_count=1,
            news_events=[
                build_event("news-1", title="Fed hints at slower rate cuts"),
            ],
        )
        telegram.preferred_language = "vi-VN"

        dispatch_summary = service.dispatch_summary(summary)

        self.assertEqual(dispatch_summary.delivered_count, 2)
        self.assertEqual(len(translator.calls), 1)
        self.assertEqual(translator.calls[0][1], "vi-VN")
        self.assertEqual(
            telegram.sent_events[0].localized_template_context["title"],
            "[vi-VN] Fed hints at slower rate cuts",
        )
        self.assertEqual(webhook.sent_events[0].template_context["title"], "Fed hints at slower rate cuts")
        self.assertFalse(webhook.sent_events[0].localized_template_context)
        telegram_attempt = next(
            attempt for attempt in dispatch_summary.attempts if attempt.sink_kind == "telegram"
        )
        self.assertEqual(telegram_attempt.requested_language, "vi-VN")
        self.assertEqual(telegram_attempt.delivered_language, "vi-VN")
        self.assertEqual(telegram_attempt.translation_status, "translated")
        webhook_attempt = next(
            attempt for attempt in dispatch_summary.attempts if attempt.sink_kind == "webhook"
        )
        self.assertIsNone(webhook_attempt.requested_language)
        self.assertEqual(webhook_attempt.translation_status, "not_needed")

    def test_dispatch_falls_back_to_source_language_when_translation_fails(self) -> None:
        telegram = FakeSink("telegram", "chat-01")
        service = NotificationService(
            sinks=[telegram],
            notifications_enabled=True,
            sink_enabled={"telegram": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
            localizer=NotificationLocalizer(translator=FakeTranslator(fail=True)),
        )
        summary = PipelineRunSummary(
            status="success",
            result="updated 1 news into graph",
            batch_id=123,
            batch_ts="20260402_101500_123",
            record_count=1,
            news_events=[build_event("news-1", title="Fed hints at slower rate cuts")],
        )
        telegram.preferred_language = "vi-VN"

        dispatch_summary = service.dispatch_summary(summary)

        self.assertEqual(dispatch_summary.delivered_count, 1)
        self.assertEqual(
            telegram.sent_events[0].template_context["title"],
            "Fed hints at slower rate cuts",
        )
        self.assertFalse(telegram.sent_events[0].localized_template_context)
        attempt = dispatch_summary.attempts[0]
        self.assertEqual(attempt.requested_language, "vi-VN")
        self.assertEqual(attempt.delivered_language, "en-US")
        self.assertEqual(attempt.translation_status, "fallback_source")
        self.assertEqual(attempt.fallback_reason, "translation backend timed out")

    def test_dispatch_skips_when_summary_not_eligible(self) -> None:
        service = NotificationService(
            notifications_enabled=True,
            sink_enabled={"telegram": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
        )
        summary = PipelineRunSummary(
            status="success",
            result="updated 0 news into graph",
            batch_id=None,
            batch_ts="20260402_101500_123",
            record_count=0,
            news_events=[],
        )

        dispatch_summary = service.dispatch_summary(summary)

        self.assertEqual(dispatch_summary.skipped_reason, "summary_not_eligible")
        self.assertEqual(dispatch_summary.total_attempts, 0)

    def test_dispatch_skips_when_notifications_disabled(self) -> None:
        service = NotificationService(
            notifications_enabled=False,
            sink_enabled={"telegram": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
        )

        dispatch_summary = service.dispatch_summary(
            PipelineRunSummary(
                status="success",
                result="updated 1 news into graph",
                batch_id=123,
                batch_ts="20260402_101500_123",
                record_count=1,
                news_events=[build_event("news-1")],
            )
        )

        self.assertEqual(dispatch_summary.skipped_reason, "notifications_disabled")
        self.assertEqual(dispatch_summary.total_attempts, 0)

    def test_dispatch_skips_when_no_enabled_sinks_are_registered(self) -> None:
        service = NotificationService(
            notifications_enabled=True,
            sink_enabled={"telegram": False, "webhook": False},
            sinks=[FakeSink("telegram", "chat-01")],
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
        )

        dispatch_summary = service.dispatch_summary(
            PipelineRunSummary(
                status="success",
                result="updated 1 news into graph",
                batch_id=123,
                batch_ts="20260402_101500_123",
                record_count=1,
                news_events=[build_event("news-1")],
            )
        )

        self.assertEqual(dispatch_summary.skipped_reason, "no_enabled_sinks")
        self.assertEqual(dispatch_summary.total_attempts, 0)

    def test_sanitize_destination_masks_sensitive_parts(self) -> None:
        self.assertEqual(
            NotificationService._sanitize_destination("https://user:secret@example.com/hook"),
            "https://example.com",
        )
        self.assertEqual(
            NotificationService._sanitize_destination("chat-12345"),
            "ch***45",
        )

    def test_sanitize_error_message_redacts_bearer_tokens_and_newlines(self) -> None:
        message = "Bearer abcdefghijklmnop\nline2"

        sanitized = NotificationService._sanitize_error_message(message)

        self.assertEqual(sanitized, "Bearer *** line2")

    @patch("opennews.notify.service.logger")
    def test_failure_log_uses_sanitized_error_message(self, logger_mock) -> None:
        webhook = FakeSink("webhook", "https://example.com/hook", fail=True)
        service = NotificationService(
            sinks=[webhook],
            notifications_enabled=True,
            sink_enabled={"webhook": True},
            policy=NotificationPolicy(timeout_seconds=5, max_attempts=1),
        )

        service.dispatch_summary(
            PipelineRunSummary(
                status="success",
                result="updated 1 news into graph",
                batch_id=123,
                batch_ts="20260402_101500_123",
                record_count=1,
                news_events=[build_event("news-1")],
            )
        )

        warning_call = logger_mock.log.call_args_list[0]
        self.assertIn("error_message=%s", warning_call.args[1])
        self.assertEqual(warning_call.args[-1], "webhook delivery failed")
