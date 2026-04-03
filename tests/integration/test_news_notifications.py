from __future__ import annotations

import unittest
from unittest.mock import patch

from opennews.config import settings
from opennews.notify.localization import NotificationLocalizer
from opennews.scheduler import polling_job
from opennews.notify.models import NewsProcessedEvent, PipelineRunSummary
from opennews.notify.service import build_notification_service


class FakeResponse:
    def raise_for_status(self) -> None:
        return None


class FailingResponse:
    def raise_for_status(self) -> None:
        raise RuntimeError("Bearer secret-token webhook downstream failed")


class FakeTranslator:
    def translate_fields(
        self,
        fields: dict[str, str],
        *,
        target_language: str,
        source_language: str | None = None,
    ) -> dict[str, str]:
        return {
            key: {
                "Fed hints at slower rate cuts": "Fed phát tín hiệu giảm tốc cắt giảm lãi suất",
                "news processed successfully": "tin đã được xử lý thành công",
            }.get(value, value)
            for key, value in fields.items()
        }


def build_summary() -> PipelineRunSummary:
    return PipelineRunSummary(
        status="success",
        result="updated 1 news into graph",
        batch_id=123,
        batch_ts="20260402_123000_111",
        record_count=1,
        news_events=[
            NewsProcessedEvent(
                batch_id=123,
                batch_ts="20260402_123000_111",
                news_id="news-123",
                title="Fed hints at slower rate cuts",
                source="seed",
                source_language="en-US",
            ).with_template_context()
        ],
    )


class TelegramIntegrationTests(unittest.TestCase):
    @patch("opennews.notify.telegram.requests.post", return_value=FakeResponse())
    def test_build_service_dispatches_telegram_from_settings(self, mock_post) -> None:
        summary = build_summary()

        original_values = {
            "notifications_enabled": settings.notifications_enabled,
            "telegram_notifications_enabled": settings.telegram_notifications_enabled,
            "telegram_bot_token": settings.telegram_bot_token,
            "telegram_chat_id": settings.telegram_chat_id,
            "telegram_template_name": settings.telegram_template_name,
            "notification_timeout_seconds": settings.notification_timeout_seconds,
        }
        try:
            settings.notifications_enabled = True
            settings.telegram_notifications_enabled = True
            settings.telegram_bot_token = "bot-token"
            settings.telegram_chat_id = "chat-01"
            settings.telegram_template_name = "default"
            settings.notification_timeout_seconds = 7

            dispatch_summary = build_notification_service().dispatch_summary(summary)

            self.assertIsNone(dispatch_summary.skipped_reason)
            self.assertEqual(dispatch_summary.delivered_count, 1)
            mock_post.assert_called_once()
            self.assertIn("/sendMessage", mock_post.call_args.args[0])
            self.assertEqual(mock_post.call_args.kwargs["json"]["chat_id"], "chat-01")
            self.assertIn("news-123", mock_post.call_args.kwargs["json"]["text"])
            self.assertEqual(mock_post.call_args.kwargs["timeout"], 7)
        finally:
            for name, value in original_values.items():
                setattr(settings, name, value)

    @patch("opennews.notify.telegram.requests.post", return_value=FakeResponse())
    @patch(
        "opennews.notify.service.build_notification_localizer",
        return_value=NotificationLocalizer(translator=FakeTranslator()),
    )
    def test_build_service_dispatches_localized_telegram_from_settings(
        self,
        _localizer_mock,
        mock_post,
    ) -> None:
        summary = build_summary()

        original_values = {
            "notifications_enabled": settings.notifications_enabled,
            "telegram_notifications_enabled": settings.telegram_notifications_enabled,
            "telegram_bot_token": settings.telegram_bot_token,
            "telegram_chat_id": settings.telegram_chat_id,
            "telegram_template_name": settings.telegram_template_name,
            "telegram_preferred_language": settings.telegram_preferred_language,
            "notification_timeout_seconds": settings.notification_timeout_seconds,
        }
        try:
            settings.notifications_enabled = True
            settings.telegram_notifications_enabled = True
            settings.telegram_bot_token = "bot-token"
            settings.telegram_chat_id = "chat-01"
            settings.telegram_template_name = "default"
            settings.telegram_preferred_language = "vi-VN"
            settings.notification_timeout_seconds = 7

            dispatch_summary = build_notification_service().dispatch_summary(summary)

            self.assertEqual(dispatch_summary.delivered_count, 1)
            attempt = dispatch_summary.attempts[0]
            self.assertEqual(attempt.requested_language, "vi-VN")
            self.assertEqual(attempt.delivered_language, "vi-VN")
            self.assertEqual(attempt.translation_status, "translated")
            self.assertIn("OpenNews vừa xử lý xong một tin", mock_post.call_args.kwargs["json"]["text"])
            self.assertIn(
                "Tiêu đề: Fed phát tín hiệu giảm tốc cắt giảm lãi suất",
                mock_post.call_args.kwargs["json"]["text"],
            )
        finally:
            for name, value in original_values.items():
                setattr(settings, name, value)

    @patch("opennews.notify.telegram.requests.post")
    def test_build_service_partial_failure_retries_and_keeps_other_sink_successful(self, mock_post) -> None:
        summary = build_summary()

        def side_effect(url, **kwargs):
            if "api.telegram.org" in url:
                return FakeResponse()
            return FailingResponse()

        mock_post.side_effect = side_effect

        original_values = {
            "notifications_enabled": settings.notifications_enabled,
            "telegram_notifications_enabled": settings.telegram_notifications_enabled,
            "telegram_bot_token": settings.telegram_bot_token,
            "telegram_chat_id": settings.telegram_chat_id,
            "telegram_template_name": settings.telegram_template_name,
            "webhook_notifications_enabled": settings.webhook_notifications_enabled,
            "webhook_url": settings.webhook_url,
            "webhook_auth_header": settings.webhook_auth_header,
            "notification_timeout_seconds": settings.notification_timeout_seconds,
            "notification_max_attempts": settings.notification_max_attempts,
        }
        try:
            settings.notifications_enabled = True
            settings.telegram_notifications_enabled = True
            settings.telegram_bot_token = "bot-token"
            settings.telegram_chat_id = "chat-01"
            settings.telegram_template_name = "default"
            settings.webhook_notifications_enabled = True
            settings.webhook_url = "https://example.com/hook"
            settings.webhook_auth_header = ""
            settings.notification_timeout_seconds = 6
            settings.notification_max_attempts = 2

            dispatch_summary = build_notification_service().dispatch_summary(summary)

            self.assertIsNone(dispatch_summary.skipped_reason)
            self.assertEqual(dispatch_summary.total_attempts, 3)
            self.assertEqual(dispatch_summary.delivered_count, 1)
            failed = [attempt for attempt in dispatch_summary.attempts if attempt.status == "failed"]
            self.assertEqual(len(failed), 2)
            self.assertEqual(failed[0].sink_kind, "webhook")
            self.assertEqual(failed[0].error_message, "Bearer *** webhook downstream failed")
        finally:
            for name, value in original_values.items():
                setattr(settings, name, value)

    @patch("opennews.scheduler.polling_job.logger")
    @patch("opennews.scheduler.polling_job.build_notification_service")
    def test_scheduler_dispatch_notifications_survives_dispatch_exception(
        self,
        build_service_mock,
        logger_mock,
    ) -> None:
        build_service_mock.return_value.dispatch_summary.side_effect = RuntimeError("dispatch boom")

        polling_job.dispatch_notifications(build_summary())

        logger_mock.exception.assert_called_once()

    @patch("opennews.notify.webhook.requests.post", return_value=FakeResponse())
    def test_build_service_dispatches_webhook_from_settings(self, mock_post) -> None:
        summary = build_summary()

        original_values = {
            "notifications_enabled": settings.notifications_enabled,
            "webhook_notifications_enabled": settings.webhook_notifications_enabled,
            "webhook_url": settings.webhook_url,
            "webhook_auth_header": settings.webhook_auth_header,
            "notification_timeout_seconds": settings.notification_timeout_seconds,
        }
        try:
            settings.notifications_enabled = True
            settings.webhook_notifications_enabled = True
            settings.webhook_url = "https://example.com/hook"
            settings.webhook_auth_header = "Authorization: Bearer secret"
            settings.notification_timeout_seconds = 4

            dispatch_summary = build_notification_service().dispatch_summary(summary)

            self.assertIsNone(dispatch_summary.skipped_reason)
            self.assertEqual(dispatch_summary.delivered_count, 1)
            mock_post.assert_called_once()
            self.assertEqual(mock_post.call_args.args[0], "https://example.com/hook")
            self.assertEqual(
                mock_post.call_args.kwargs["headers"]["Authorization"],
                "Bearer secret",
            )
            self.assertEqual(mock_post.call_args.kwargs["json"]["news"]["id"], "news-123")
            self.assertEqual(mock_post.call_args.kwargs["timeout"], 4)
        finally:
            for name, value in original_values.items():
                setattr(settings, name, value)

    @patch("opennews.notify.telegram.requests.post", return_value=FakeResponse())
    def test_build_service_dispatches_multi_sink_from_settings(self, mock_post) -> None:
        summary = build_summary()

        original_values = {
            "notifications_enabled": settings.notifications_enabled,
            "telegram_notifications_enabled": settings.telegram_notifications_enabled,
            "telegram_bot_token": settings.telegram_bot_token,
            "telegram_chat_id": settings.telegram_chat_id,
            "telegram_template_name": settings.telegram_template_name,
            "webhook_notifications_enabled": settings.webhook_notifications_enabled,
            "webhook_url": settings.webhook_url,
            "webhook_auth_header": settings.webhook_auth_header,
            "notification_timeout_seconds": settings.notification_timeout_seconds,
        }
        try:
            settings.notifications_enabled = True
            settings.telegram_notifications_enabled = True
            settings.telegram_bot_token = "bot-token"
            settings.telegram_chat_id = "chat-01"
            settings.telegram_template_name = "default"
            settings.webhook_notifications_enabled = True
            settings.webhook_url = "https://example.com/hook"
            settings.webhook_auth_header = ""
            settings.notification_timeout_seconds = 6

            dispatch_summary = build_notification_service().dispatch_summary(summary)

            self.assertIsNone(dispatch_summary.skipped_reason)
            self.assertEqual(dispatch_summary.delivered_count, 2)
            self.assertEqual(mock_post.call_count, 2)
            urls = [call.args[0] for call in mock_post.call_args_list]
            self.assertTrue(any("/sendMessage" in url for url in urls))
            self.assertTrue(any(url == "https://example.com/hook" for url in urls))
        finally:
            for name, value in original_values.items():
                setattr(settings, name, value)
