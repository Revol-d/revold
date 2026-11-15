"""Testa o HttpWebhookSender de ponta a ponta contra um app FastAPI de
verdade (ASGITransport do httpx — sem precisar de porta/servidor real),
inclusive o retry/backoff em caso de falha (mesmo espírito do teste de
contrato do api-gateway: ASGI real, sem infraestrutura de rede).
"""
from __future__ import annotations

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport

from revold_messaging.http_webhook_sender import HttpWebhookSender
from revold_platform.events.domain import DomainEvent


def _make_app(responses: list[int]) -> tuple[FastAPI, list[dict]]:
    """App de teste que devolve os status codes de `responses` em ordem, um
    por chamada recebida (a última é reusada se houver mais chamadas que
    itens na lista) — permite simular "falhou, falhou, deu certo"."""
    app = FastAPI()
    received: list[dict] = []
    calls = {"count": 0}

    @app.post("/webhook")
    async def webhook(request: Request) -> Response:
        body = await request.json()
        received.append(body)
        index = min(calls["count"], len(responses) - 1)
        calls["count"] += 1
        status = responses[index]
        return Response(status_code=status, content=b"{}", media_type="application/json")

    return app, received


async def test_send_com_sucesso_na_primeira_tentativa() -> None:
    app, received = _make_app([200])
    sender = HttpWebhookSender(
        max_attempts=3, backoff_base_seconds=0.01, transport=ASGITransport(app=app)
    )
    event = DomainEvent(name="checkout.created", payload={"cart_id": "abc"})

    result = await sender.send("http://webhook.test/webhook", event)

    assert result is True
    assert received == [{"name": "checkout.created", "payload": {"cart_id": "abc"}}]


async def test_send_tenta_de_novo_apos_falha_e_depois_da_certo() -> None:
    app, received = _make_app([500, 500, 200])
    sender = HttpWebhookSender(
        max_attempts=3, backoff_base_seconds=0.01, transport=ASGITransport(app=app)
    )
    event = DomainEvent(name="stock.low", payload={"sku": "CAM-001-P"})

    result = await sender.send("http://webhook.test/webhook", event)

    assert result is True
    assert len(received) == 3


async def test_send_esgota_tentativas_e_retorna_falso() -> None:
    app, received = _make_app([500, 500, 500])
    sender = HttpWebhookSender(
        max_attempts=3, backoff_base_seconds=0.01, transport=ASGITransport(app=app)
    )
    event = DomainEvent(name="product.updated", payload={"sku": "CAM-001"})

    result = await sender.send("http://webhook.test/webhook", event)

    assert result is False
    assert len(received) == 3
