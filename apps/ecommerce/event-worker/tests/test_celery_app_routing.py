"""Testa o roteamento de event_worker.celery_app._dispatch (qual handler
chama pra cada event_name) sem precisar de Celery nem Redis nem Azure SQL
de verdade — monkeypatcha revold_ecommerce.application.event_handlers.handle_* e chama
_dispatch diretamente. A entrega de verdade via Celery+Redis é
test_integration_worker.py (marker integration); a lógica de negócio de
cada handler é products/ecommerce/tests/test_event_handlers.py."""
from __future__ import annotations

from event_worker import celery_app
from revold_ecommerce.application import event_handlers


async def test_dispatch_roteia_product_updated(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_handle_product_updated(payload, **kwargs):
        calls.append(payload)
        return True

    monkeypatch.setattr(event_handlers, "handle_product_updated", _fake_handle_product_updated)

    await celery_app._dispatch("product.updated", {"sku": "P1"})

    assert calls == [{"sku": "P1"}]


async def test_dispatch_roteia_checkout_created(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_handle_checkout_created(payload, **kwargs):
        calls.append(payload)

    monkeypatch.setattr(celery_app.event_handlers, "handle_checkout_created", _fake_handle_checkout_created)

    await celery_app._dispatch("checkout.created", {"cart_id": "c1", "summary_text": "x"})

    assert calls == [{"cart_id": "c1", "summary_text": "x"}]


async def test_dispatch_roteia_stock_low(monkeypatch) -> None:
    calls: list[dict] = []

    async def _fake_handle_stock_low(payload, **kwargs):
        calls.append(payload)

    monkeypatch.setattr(celery_app.event_handlers, "handle_stock_low", _fake_handle_stock_low)

    await celery_app._dispatch("stock.low", {"sku": "A", "quantity_available": 1, "threshold": 5})

    assert calls == [{"sku": "A", "quantity_available": 1, "threshold": 5}]


async def test_dispatch_evento_desconhecido_nao_levanta_erro() -> None:
    """Extensibilidade: publicar um evento sem handler ainda não deve
    derrubar o worker — é o caso esperado quando um core começa a publicar
    um evento novo antes do handler correspondente existir."""
    await celery_app._dispatch("algo.inexistente", {})


async def test_dispatch_sem_webhook_urls_nao_encaminha_nada(monkeypatch) -> None:
    monkeypatch.delenv("WEBHOOK_URLS", raising=False)
    calls: list[str] = []

    async def _fake_forward_to_webhooks(event, *, webhook_urls, sender):
        calls.append(event.name)
        return {}

    monkeypatch.setattr(event_handlers, "forward_to_webhooks", _fake_forward_to_webhooks)

    await celery_app._dispatch("algo.inexistente", {})

    assert calls == []


async def test_dispatch_com_webhook_urls_configuradas_encaminha_o_evento(monkeypatch) -> None:
    monkeypatch.setenv("WEBHOOK_URLS", "https://parceiro.example.com/hook, https://outro.example.com/hook")
    forwarded: list[tuple] = []

    async def _fake_handle_product_updated(payload, **kwargs):
        return True

    async def _fake_forward_to_webhooks(event, *, webhook_urls, sender):
        forwarded.append((event.name, webhook_urls))
        return {url: True for url in webhook_urls}

    monkeypatch.setattr(event_handlers, "handle_product_updated", _fake_handle_product_updated)
    monkeypatch.setattr(event_handlers, "forward_to_webhooks", _fake_forward_to_webhooks)

    await celery_app._dispatch("product.updated", {"sku": "CAM-001"})

    assert forwarded == [
        ("product.updated", ["https://parceiro.example.com/hook", "https://outro.example.com/hook"])
    ]
