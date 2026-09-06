"""Seleciona a implementação de WebhookSender a partir de
WEBHOOK_SENDER_PROVIDER (ADR-0016). Mesmo padrão de
adapters_external.notification.factory / adapters_external.media.factory.
"""
from __future__ import annotations

import os

from core_events.ports import WebhookSender


def get_webhook_sender() -> WebhookSender:
    provider = os.environ.get("WEBHOOK_SENDER_PROVIDER", "logging")
    if provider == "logging":
        from adapters_messaging.webhooks.logging_webhook_sender import LoggingWebhookSender

        return LoggingWebhookSender()
    if provider == "http":
        from adapters_messaging.webhooks.http_webhook_sender import HttpWebhookSender

        return HttpWebhookSender()
    raise ValueError(f"WEBHOOK_SENDER_PROVIDER desconhecido: {provider!r}")


def get_webhook_urls() -> list[str]:
    raw = os.environ.get("WEBHOOK_URLS", "")
    return [url.strip() for url in raw.split(",") if url.strip()]
