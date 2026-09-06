"""Adapter real de core_notification.ports.NotificationChannel via e-mail
SMTP (ADR-0018). Diferente de Azure AD/Google/WhatsApp Business API, uma
conta SMTP (SendGrid, SES, ou até um Gmail com senha de app) é trivial de
conseguir — não depende de negociação corporativa nem de aprovação de
terceiros.

Testado de ponta a ponta contra o aiosmtpd (servidor SMTP real, em memória,
puro Python — sem precisar de Docker/Mailpit, que não estão disponíveis
neste ambiente de nuvem) em
adapters/external/tests/test_smtp_channel.py.
"""
from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from core_notification.domain import Notification


class SmtpNotificationChannel:
    provider_name = "smtp"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_address: str,
        to_address: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._from_address = from_address
        self._to_address = to_address
        self._username = username
        self._password = password
        self._use_tls = use_tls

    def _build_message(self, notification: Notification) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = self._to_address
        message["Subject"] = f"[revold] {notification.event_type}"
        message.set_content(notification.message)
        return message

    async def send(self, notification: Notification) -> None:
        message = self._build_message(notification)
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
        )
