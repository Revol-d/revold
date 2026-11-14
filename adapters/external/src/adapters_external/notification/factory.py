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
    if provider == "whatsapp-business":
        from adapters_external.notification.whatsapp_business_channel import (
            WhatsAppBusinessNotificationChannel,
        )

        access_token = os.environ.get("WHATSAPP_BUSINESS_ACCESS_TOKEN")
        phone_number_id = os.environ.get("WHATSAPP_BUSINESS_PHONE_NUMBER_ID")
        recipient_number = os.environ.get("NICK_WHATSAPP_NUMBER")
        if not (access_token and phone_number_id and recipient_number):
            raise NotImplementedError(
                "NOTIFICATION_PROVIDER=whatsapp-business requer "
                "WHATSAPP_BUSINESS_ACCESS_TOKEN, WHATSAPP_BUSINESS_PHONE_NUMBER_ID e "
                "NICK_WHATSAPP_NUMBER configurados (ver .env.example e ADR-0025)."
            )
        return WhatsAppBusinessNotificationChannel(
            access_token=access_token,
            phone_number_id=phone_number_id,
            recipient_number=recipient_number,
            template_name=os.environ.get("WHATSAPP_BUSINESS_TEMPLATE_NAME"),
        )
    raise ValueError(f"NOTIFICATION_PROVIDER desconhecido: {provider!r}")
