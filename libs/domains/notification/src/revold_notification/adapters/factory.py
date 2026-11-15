"""Seleciona a implementação de NotificationChannel a partir de `NotificationSettings`.

Mesmo padrão das outras factories (ADR-0003/ADR-0011): trocar de canal em produção é mudar a
configuração, nunca importar um adapter diferente manualmente em outro módulo.

Este módulo não lê o ambiente. O `settings.py` do app lê e entrega um `NotificationSettings`
pronto (em geral via `NotificationSettings.from_mapping(env_snapshot())`). Os nomes das chaves
são os do `.env.example`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from revold_notification.adapters.logging_channel import LoggingNotificationChannel
from revold_notification.ports import NotificationChannel

_TRUE = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True)
class NotificationSettings:
    """Configuração do canal de notificação. Segredo fica fora do `repr`."""

    provider: str = "logging"
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_from_address: str | None = None
    smtp_username: str | None = None
    smtp_password: str | None = field(default=None, repr=False)
    smtp_use_tls: bool = True
    notification_email: str | None = None
    whatsapp_access_token: str | None = field(default=None, repr=False)
    whatsapp_phone_number_id: str | None = None
    whatsapp_recipient_number: str | None = None
    whatsapp_template_name: str | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> NotificationSettings:
        """Monta a configuração a partir de um mapeamento com as chaves do `.env.example`."""
        port = values.get("SMTP_PORT")
        return cls(
            provider=values.get("NOTIFICATION_PROVIDER", "logging"),
            smtp_host=values.get("SMTP_HOST"),
            smtp_port=int(port) if port else None,
            smtp_from_address=values.get("SMTP_FROM_ADDRESS"),
            smtp_username=values.get("SMTP_USERNAME"),
            smtp_password=values.get("SMTP_PASSWORD"),
            smtp_use_tls=values.get("SMTP_USE_TLS", "true").lower() == "true",
            notification_email=values.get("NICK_NOTIFICATION_EMAIL"),
            whatsapp_access_token=values.get("WHATSAPP_BUSINESS_ACCESS_TOKEN"),
            whatsapp_phone_number_id=values.get("WHATSAPP_BUSINESS_PHONE_NUMBER_ID"),
            whatsapp_recipient_number=values.get("NICK_WHATSAPP_NUMBER"),
            whatsapp_template_name=values.get("WHATSAPP_BUSINESS_TEMPLATE_NAME"),
        )


def build_notification_channel(settings: NotificationSettings | None = None) -> NotificationChannel:
    settings = settings or NotificationSettings()
    provider = settings.provider
    if provider == "logging":
        return LoggingNotificationChannel()
    if provider == "smtp":
        from revold_notification.adapters.smtp_channel import SmtpNotificationChannel

        if not (
            settings.smtp_host
            and settings.smtp_port
            and settings.smtp_from_address
            and settings.notification_email
        ):
            raise NotImplementedError(
                "NOTIFICATION_PROVIDER=smtp requer SMTP_HOST, SMTP_PORT, "
                "SMTP_FROM_ADDRESS e NICK_NOTIFICATION_EMAIL configurados "
                "(ver .env.example e ADR-0018)."
            )
        return SmtpNotificationChannel(
            host=settings.smtp_host,
            port=settings.smtp_port,
            from_address=settings.smtp_from_address,
            to_address=settings.notification_email,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )
    if provider == "whatsapp-business":
        from revold_notification.adapters.whatsapp_business_channel import (
            WhatsAppBusinessNotificationChannel,
        )

        if not (
            settings.whatsapp_access_token
            and settings.whatsapp_phone_number_id
            and settings.whatsapp_recipient_number
        ):
            raise NotImplementedError(
                "NOTIFICATION_PROVIDER=whatsapp-business requer "
                "WHATSAPP_BUSINESS_ACCESS_TOKEN, WHATSAPP_BUSINESS_PHONE_NUMBER_ID e "
                "NICK_WHATSAPP_NUMBER configurados (ver .env.example e ADR-0025)."
            )
        return WhatsAppBusinessNotificationChannel(
            access_token=settings.whatsapp_access_token,
            phone_number_id=settings.whatsapp_phone_number_id,
            recipient_number=settings.whatsapp_recipient_number,
            template_name=settings.whatsapp_template_name,
        )
    raise ValueError(f"NOTIFICATION_PROVIDER desconhecido: {provider!r}")
