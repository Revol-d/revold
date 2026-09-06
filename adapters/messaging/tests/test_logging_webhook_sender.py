from __future__ import annotations

from adapters_messaging.webhooks.logging_webhook_sender import LoggingWebhookSender
from core_events.domain import DomainEvent


async def test_send_registra_o_evento_e_sempre_retorna_sucesso() -> None:
    sender = LoggingWebhookSender()
    event = DomainEvent(name="product.updated", payload={"sku": "CAM-001"})

    result = await sender.send("https://parceiro.example.com/webhook", event)

    assert result is True
    assert sender.sent == [("https://parceiro.example.com/webhook", event)]
