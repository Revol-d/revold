from __future__ import annotations

from revold_platform.events.logging_webhook_sender import LoggingWebhookSender
from revold_platform.events.domain import DomainEvent


async def test_send_registra_o_evento_e_sempre_retorna_sucesso() -> None:
    sender = LoggingWebhookSender()
    event = DomainEvent(name="product.updated", payload={"sku": "CAM-001"})

    result = await sender.send("https://parceiro.example.com/webhook", event)

    assert result is True
    assert sender.sent == [("https://parceiro.example.com/webhook", event)]
