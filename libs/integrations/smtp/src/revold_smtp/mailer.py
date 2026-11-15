"""Envio de e-mail por SMTP (aiosmtplib).

Uma conta SMTP (SendGrid, SES, ou um Gmail com senha de app) é trivial de conseguir e não
depende de aprovação de terceiros. O cliente é exercitado de ponta a ponta contra o aiosmtpd
(servidor SMTP real, em memória) pelos testes do canal de notificação.
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib


class SmtpMailer:
    """Conexão com um servidor SMTP. Recebe a configuração por parâmetro, nunca do ambiente."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls

    async def send(self, message: EmailMessage) -> None:
        """Entrega a mensagem. Erro do servidor sobe para quem chamou."""
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
        )
