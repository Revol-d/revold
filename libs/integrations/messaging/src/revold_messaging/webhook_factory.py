"""Seleciona a implementação de WebhookSender pelo nome do provedor (ADR-0016).

O nome vem do `settings.py` do app (variável `WEBHOOK_SENDER_PROVIDER`), assim como a lista de
destinos (`WEBHOOK_URLS`). Este módulo não lê o ambiente.
"""

from __future__ import annotations

from revold_platform.events.ports import WebhookSender

DEFAULT_WEBHOOK_SENDER_PROVIDER = "logging"


def build_webhook_sender(provider: str = DEFAULT_WEBHOOK_SENDER_PROVIDER) -> WebhookSender:
    if provider == "logging":
        from revold_platform.events.logging_webhook_sender import LoggingWebhookSender

        return LoggingWebhookSender()
    if provider == "http":
        from revold_messaging.http_webhook_sender import HttpWebhookSender

        return HttpWebhookSender()
    raise ValueError(f"WEBHOOK_SENDER_PROVIDER desconhecido: {provider!r}")
