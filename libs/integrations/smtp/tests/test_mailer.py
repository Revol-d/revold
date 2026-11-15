"""O `SmtpMailer` contra o aiosmtpd: um servidor SMTP de verdade, em memória, sem credencial."""

from __future__ import annotations

import socket
from email.message import EmailMessage

import pytest
from aiosmtpd.controller import Controller

from revold_smtp.mailer import SmtpMailer

pytestmark = pytest.mark.integration


class _RecordingHandler:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802 — nome exigido pelo aiosmtpd
        self.messages.append(
            {
                "mail_from": envelope.mail_from,
                "rcpt_tos": list(envelope.rcpt_tos),
                "content": envelope.content.decode("utf-8", errors="replace"),
            }
        )
        return "250 Message accepted for delivery"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def smtp_server():
    handler = _RecordingHandler()
    port = _free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    yield handler, port
    controller.stop()


def _message(subject: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message["Subject"] = subject
    message.set_content("corpo da mensagem")
    return message


async def test_send_delivers_the_message_it_receives(smtp_server) -> None:
    handler, port = smtp_server
    mailer = SmtpMailer(host="127.0.0.1", port=port, use_tls=False)

    await mailer.send(_message("assunto de teste"))

    assert len(handler.messages) == 1
    delivered = handler.messages[0]
    assert delivered["mail_from"] == "sender@example.com"
    assert delivered["rcpt_tos"] == ["recipient@example.com"]
    assert "assunto de teste" in delivered["content"]
    assert "corpo da mensagem" in delivered["content"]


async def test_send_raises_when_the_server_is_unreachable() -> None:
    """Erro de entrega sobe para quem chamou: o cliente não engole falha."""
    mailer = SmtpMailer(host="127.0.0.1", port=_free_port(), use_tls=False)

    with pytest.raises(OSError):
        await mailer.send(_message("nao chega"))
