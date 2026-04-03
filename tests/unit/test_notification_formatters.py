from __future__ import annotations

import unittest

from opennews.notify.models import NewsProcessedEvent
from opennews.notify.telegram import render_telegram_message
from opennews.notify.webhook import build_webhook_payload


def build_event() -> NewsProcessedEvent:
    return NewsProcessedEvent(
        batch_id=321,
        batch_ts="20260402_123000_111",
        news_id="news-123",
        title="Fed hints at slower rate cuts",
        source="seed",
        result="news processed successfully",
        completed_at="2026-04-02T12:30:05+00:00",
    ).with_template_context()


class TelegramFormatterTests(unittest.TestCase):
    def test_default_template_renders_expected_fields(self) -> None:
        message = render_telegram_message(build_event())

        self.assertIn("OpenNews processed a news item", message)
        self.assertIn("Batch ID: 321", message)
        self.assertIn("News ID: news-123", message)
        self.assertIn("Title: Fed hints at slower rate cuts", message)

    def test_vietnamese_template_prefers_localized_context(self) -> None:
        event = build_event()
        event.preferred_language = "vi-VN"
        event.localized_template_context = {
            **event.template_context,
            "title": "Fed phát tín hiệu giảm tốc cắt giảm lãi suất",
            "result": "tin đã được xử lý thành công",
        }

        message = render_telegram_message(event)

        self.assertIn("OpenNews vừa xử lý xong một tin", message)
        self.assertIn("Mã batch: 321", message)
        self.assertIn("Tiêu đề: Fed phát tín hiệu giảm tốc cắt giảm lãi suất", message)
        self.assertIn("Kết quả: tin đã được xử lý thành công", message)

    def test_unknown_template_raises(self) -> None:
        with self.assertRaises(ValueError):
            render_telegram_message(build_event(), template_name="unknown")

    def test_webhook_payload_mapping_contains_expected_fields(self) -> None:
        payload = build_webhook_payload(build_event())

        self.assertEqual(payload["event_type"], "news_processed")
        self.assertEqual(payload["batch"]["id"], 321)
        self.assertEqual(payload["news"]["id"], "news-123")
        self.assertEqual(payload["news"]["title"], "Fed hints at slower rate cuts")
        self.assertEqual(payload["result"]["summary"], "news processed successfully")
