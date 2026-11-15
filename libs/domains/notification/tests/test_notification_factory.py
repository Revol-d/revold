from __future__ import annotations

import pytest

from revold_notification.adapters.factory import NotificationSettings, build_notification_channel
from revold_notification.adapters.logging_channel import LoggingNotificationChannel
from revold_notification.adapters.smtp_channel import SmtpNotificationChannel
from revold_notification.adapters.whatsapp_business_channel import (
    WhatsAppBusinessNotificationChannel,
)


def test_default_e_logging() -> None:
    channel = build_notification_channel()

    assert isinstance(channel, LoggingNotificationChannel)


def test_mapeamento_vazio_cai_no_logging() -> None:
    channel = build_notification_channel(NotificationSettings.from_mapping({}))

    assert isinstance(channel, LoggingNotificationChannel)


def test_provider_logging_explicito() -> None:
    settings = NotificationSettings.from_mapping({"NOTIFICATION_PROVIDER": "logging"})

    channel = build_notification_channel(settings)

    assert isinstance(channel, LoggingNotificationChannel)


def test_provider_smtp_sem_configuracao_levanta_not_implemented() -> None:
    settings = NotificationSettings.from_mapping({"NOTIFICATION_PROVIDER": "smtp"})

    with pytest.raises(NotImplementedError):
        build_notification_channel(settings)


def test_provider_smtp_configurado_devolve_smtp_channel() -> None:
    settings = NotificationSettings.from_mapping(
        {
            "NOTIFICATION_PROVIDER": "smtp",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_FROM_ADDRESS": "revold@example.com",
            "NICK_NOTIFICATION_EMAIL": "nick@example.com",
        }
    )

    channel = build_notification_channel(settings)

    assert isinstance(channel, SmtpNotificationChannel)


def test_provider_whatsapp_business_sem_configuracao_levanta_not_implemented() -> None:
    settings = NotificationSettings.from_mapping({"NOTIFICATION_PROVIDER": "whatsapp-business"})

    with pytest.raises(NotImplementedError):
        build_notification_channel(settings)


def test_provider_whatsapp_business_configurado_devolve_o_canal() -> None:
    settings = NotificationSettings.from_mapping(
        {
            "NOTIFICATION_PROVIDER": "whatsapp-business",
            "WHATSAPP_BUSINESS_ACCESS_TOKEN": "token-de-teste",
            "WHATSAPP_BUSINESS_PHONE_NUMBER_ID": "123456",
            "NICK_WHATSAPP_NUMBER": "5511999999999",
        }
    )

    channel = build_notification_channel(settings)

    assert isinstance(channel, WhatsAppBusinessNotificationChannel)


def test_provider_desconhecido_levanta_value_error() -> None:
    settings = NotificationSettings.from_mapping({"NOTIFICATION_PROVIDER": "carta-registrada"})

    with pytest.raises(ValueError):
        build_notification_channel(settings)


def test_smtp_use_tls_so_desliga_com_false() -> None:
    assert NotificationSettings.from_mapping({}).smtp_use_tls is True
    assert NotificationSettings.from_mapping({"SMTP_USE_TLS": "false"}).smtp_use_tls is False


def test_segredo_nao_aparece_no_repr() -> None:
    settings = NotificationSettings(smtp_password="senha-de-teste", whatsapp_access_token="token-x")
    assert "senha-de-teste" not in repr(settings)
    assert "token-x" not in repr(settings)
