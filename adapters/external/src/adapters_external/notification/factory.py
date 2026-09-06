"""Seleciona a implementação de NotificationChannel a partir de
NOTIFICATION_PROVIDER.

Mesmo padrão de adapters_external.ai.factory / adapters_external.identity.factory
(ADR-0003/ADR-0011): trocar de canal em produção é mudar a variável de
ambiente, nunca importar um adapter diferente manualmente em outro módulo.
"""
from __future__ import annotations

import os

from core_notification.ports import NotificationChannel

from adapters_external.notification.logging_channel import LoggingNotificationChannel


def get_notification_channel() -> NotificationChannel:
    provider = os.environ.get("NOTIFICATION_PROVIDER", "logging")
    if provider == "logging":
        return LoggingNotificationChannel()
    if provider == "smtp":
        from adapters_external.notification.smtp_channel import SmtpNotificationChannel

        host = os.environ.get("SMTP_HOST")
        port = os.environ.get("SMTP_PORT")
        from_address = os.environ.get("SMTP_FROM_ADDRESS")
        to_address = os.environ.get("NICK_NOTIFICATION_EMAIL")
        if not (host and port and from_address and to_address):
            raise NotImplementedError(
                "NOTIFICATION_PROVIDER=smtp requer SMTP_HOST, SMTP_PORT, "
                "SMTP_FROM_ADDRESS e NICK_NOTIFICATION_EMAIL configurados "
                "(ver .env.example e ADR-0018)."
            )
        return SmtpNotificationChannel(
            host=host,
            port=int(port),
            from_address=from_address,
            to_address=to_address,
            username=os.environ.get("SMTP_USERNAME"),
            password=os.environ.get("SMTP_PASSWORD"),
            use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
        )
    raise ValueError(f"NOTIFICATION_PROVIDER desconhecido: {provider!r}")
