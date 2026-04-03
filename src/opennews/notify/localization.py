from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from typing import Protocol

from opennews.llm.client import LLMClient, LLMConfig
from opennews.notify.models import NewsProcessedEvent

logger = logging.getLogger(__name__)


class NotificationTranslator(Protocol):
    def translate_fields(
        self,
        fields: dict[str, str],
        *,
        target_language: str,
        source_language: str | None = None,
    ) -> dict[str, str]:
        ...


@dataclass(slots=True)
class LocalizationResult:
    event: NewsProcessedEvent
    requested_language: str | None
    delivered_language: str | None
    translation_status: str
    fallback_reason: str | None = None


class LLMNotificationTranslator:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.load()
        self._client = LLMClient(self.config)

    def translate_fields(
        self,
        fields: dict[str, str],
        *,
        target_language: str,
        source_language: str | None = None,
    ) -> dict[str, str]:
        if not self.config.api_key:
            raise RuntimeError("notification translator is not configured")

        payload = json.dumps(fields, ensure_ascii=False)
        system = (
            "You translate short notification fields for operators. "
            "Return only JSON with the same keys you received. "
            "Preserve identifiers, URLs, and proper nouns unless natural translation is obvious."
        )
        user = (
            f"Translate the JSON values into {target_language}.\n"
            f"Source language: {source_language or 'unknown'}.\n"
            "Keep the same keys and output valid JSON only.\n"
            f"Input: {payload}"
        )
        raw = self._client.chat(system, user)
        translated = self._parse_json_object(raw)
        return {
            key: str(translated.get(key, value))
            for key, value in fields.items()
        }

    @staticmethod
    def _parse_json_object(raw: str) -> dict[str, str]:
        json_match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        text = json_match.group(1).strip() if json_match else raw.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            brace_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not brace_match:
                raise RuntimeError("translation response did not contain JSON")
            try:
                parsed = json.loads(brace_match.group())
            except json.JSONDecodeError as exc:
                raise RuntimeError("translation response could not be parsed") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("translation response must be a JSON object")
        return {
            str(key): str(value)
            for key, value in parsed.items()
            if value is not None
        }


class NotificationLocalizer:
    def __init__(self, translator: NotificationTranslator | None = None) -> None:
        self._translator = translator

    def localize_event(
        self,
        event: NewsProcessedEvent,
        *,
        target_language: str | None,
        sink_kind: str | None = None,
    ) -> LocalizationResult:
        event.with_template_context()
        normalized_target = (target_language or "").strip()
        if not normalized_target:
            return LocalizationResult(
                event=event,
                requested_language=None,
                delivered_language=None,
                translation_status="not_needed",
            )

        if sink_kind and sink_kind != "telegram":
            return LocalizationResult(
                event=event,
                requested_language=None,
                delivered_language=None,
                translation_status="not_needed",
            )

        if self._same_language(event.source_language, normalized_target):
            return LocalizationResult(
                event=self._copy_event(
                    event,
                    preferred_language=normalized_target,
                    localized_context=dict(event.template_context),
                ),
                requested_language=normalized_target,
                delivered_language=normalized_target,
                translation_status="not_needed",
            )

        if self._translator is None:
            return LocalizationResult(
                event=event,
                requested_language=normalized_target,
                delivered_language=event.source_language or "source",
                translation_status="fallback_source",
                fallback_reason="translator unavailable",
            )

        fields = {
            "title": event.template_context.get("title") or event.resolved_title(),
            "result": event.template_context.get("result") or event.result,
        }
        try:
            translated_fields = self._translator.translate_fields(
                fields,
                target_language=normalized_target,
                source_language=event.source_language,
            )
        except Exception as exc:
            logger.warning(
                "notification localization failed: sink=%s news_id=%s target_language=%s error=%s",
                sink_kind or "unknown",
                event.news_id,
                normalized_target,
                exc,
            )
            return LocalizationResult(
                event=event,
                requested_language=normalized_target,
                delivered_language=event.source_language or "source",
                translation_status="fallback_source",
                fallback_reason=str(exc),
            )

        localized_context = dict(event.template_context)
        localized_context.update(translated_fields)
        localized_event = self._copy_event(
            event,
            preferred_language=normalized_target,
            localized_context=localized_context,
        )
        return LocalizationResult(
            event=localized_event,
            requested_language=normalized_target,
            delivered_language=normalized_target,
            translation_status="translated",
        )

    @staticmethod
    def _copy_event(
        event: NewsProcessedEvent,
        *,
        preferred_language: str | None,
        localized_context: dict[str, str] | None = None,
    ) -> NewsProcessedEvent:
        return replace(
            event,
            preferred_language=preferred_language,
            localized_template_context=localized_context or {},
        )

    @staticmethod
    def _same_language(source_language: str | None, target_language: str | None) -> bool:
        if not source_language or not target_language:
            return False
        return source_language.split("-", 1)[0].lower() == target_language.split("-", 1)[0].lower()
