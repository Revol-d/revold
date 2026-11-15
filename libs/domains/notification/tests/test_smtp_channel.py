"""Testa o SmtpNotificationChannel de ponta a ponta contra o aiosmtpd — um
servidor SMTP real, em memória, puro Python (sem precisar de
Docker/Mailpit, que não estão disponíveis neste ambiente de nuvem). Prova
que a mensagem é formatada e entregue via protocolo SMTP de verdade, não
via mock da chamada de rede. `use_tls=False` aqui porque o aiosmtpd de
teste não expõe TLS — em produção, um provedor real (SendGrid, SES etc.)
sempre usa TLS (ver ADR-0018)."""
from __future__ import annotations

import socket

import pytest
from aiosmtpd.controller import Controller

from revold_notification.adapters.smtp_channel import SmtpNotificationChannel
from revold_notification.domain import Notification

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


@pytest.fixture
def channel(smtp_server):
    _handler, port = smtp_server
    return SmtpNotificationChannel(
        host="127.0.0.1",
        port=port,
        from_address="revold@example.com",
        to_address="nick@example.com",
        use_tls=False,
    )


async def test_send_entrega_a_mensagem_de_verdade_via_smtp(smtp_server, channel) -> None:
    handler, _port = smtp_server
    notification = Notification(event_type="new_checkout", message="Novo pedido: 2x Camiseta")

    await channel.send(notification)

    assert len(handler.messages) == 1
    delivered = handler.messages[0]
    assert delivered["mail_from"] == "revold@example.com"
    assert delivered["rcpt_tos"] == ["nick@example.com"]
    assert "[revold] new_checkout" in delivered["content"]
    assert "Novo pedido: 2x Camiseta" in delivered["content"]


async def test_send_de_multiplas_notificacoes_entrega_todas(smtp_server, channel) -> None:
    handler, _port = smtp_server

    await channel.send(Notification(event_type="new_checkout", message="Pedido 1"))
    await channel.send(Notification(event_type="low_stock", message="SKU X com pouco estoque"))

    assert len(handler.messages) == 2
    assert "[revold] new_checkout" in handler.messages[0]["content"]
    assert "[revold] low_stock" in handler.messages[1]["content"]
