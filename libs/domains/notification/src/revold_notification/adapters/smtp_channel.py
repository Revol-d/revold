"""Adapter real de revold_notification.ports.NotificationChannel via e-mail
SMTP (ADR-0018). Diferente de Azure AD/Google/WhatsApp Business API, uma
conta SMTP (SendGrid, SES, ou até um Gmail com senha de app) é trivial de
conseguir — não depende de negociação corporativa nem de aprovação de
terceiros.

Este adapter só monta a mensagem a partir da notificação. Quem fala com o
servidor é o cliente `revold_smtp.mailer.SmtpMailer` (libs/integrations/smtp).

Testado de ponta a ponta contra o aiosmtpd (servidor SMTP real, em memória,
puro Python — sem precisar de Docker/Mailpit, que não estão disponíveis
neste ambiente de nuvem) em
libs/domains/notification/tests/test_smtp_channel.py.
"""
from __future__ import annotations

from email.message import EmailMessage

from revold_notification.domain import Notification
from revold_smtp.mailer import SmtpMailer


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
        self._mailer = SmtpMailer(
            host=host, port=port, username=username, password=password, use_tls=use_tls
        )
        self._from_address = from_address
        self._to_address = to_address

    def _build_message(self, notification: Notification) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = self._to_address
        message["Subject"] = f"[revold] {notification.event_type}"
        message.set_content(notification.message)
        return message

    async def send(self, notification: Notification) -> None:
        await self._mailer.send(self._build_message(notification))
