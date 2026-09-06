from __future__ import annotations

import pytest

from adapters_external.notification.factory import get_notification_channel
from adapters_external.notification.logging_channel import LoggingNotificationChannel
from adapters_external.notification.smtp_channel import SmtpNotificationChannel


def test_default_e_logging(monkeypatch) -> None:
    monkeypatch.delenv("NOTIFICATION_PROVIDER", raising=False)

    channel = get_notification_channel()

    assert isinstance(channel, LoggingNotificationChannel)


def test_provider_logging_explicito(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFICATION_PROVIDER", "logging")

    channel = get_notification_channel()

    assert isinstance(channel, LoggingNotificationChannel)


def test_provider_smtp_sem_configuracao_levanta_not_implemented(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFICATION_PROVIDER", "smtp")
    for var in ("SMTP_HOST", "SMTP_PORT", "SMTP_FROM_ADDRESS", "NICK_NOTIFICATION_EMAIL"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(NotImplementedError):
        get_notification_channel()


def test_provider_smtp_configurado_devolve_smtp_channel(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFICATION_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "revold@example.com")
    monkeypatch.setenv("NICK_NOTIFICATION_EMAIL", "nick@example.com")

    channel = get_notification_channel()

    assert isinstance(channel, SmtpNotificationChannel)


def test_provider_desconhecido_levanta_value_error(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFICATION_PROVIDER", "carta-registrada")

    with pytest.raises(ValueError):
        get_notification_channel()
