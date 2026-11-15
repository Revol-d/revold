"""Testa revold_ecommerce.application.event_handlers com fakes — sem Celery, sem Redis, sem
Postgres. O round-trip real (publicar -> worker consumir) é
tests/test_integration_worker.py."""
from __future__ import annotations

from decimal import Decimal

from revold_ecommerce.application.event_handlers import (
    forward_to_webhooks,
    handle_checkout_created,
    handle_product_updated,
    handle_stock_low,
)

from revold_catalog.domain import Category, Money, Product, ProductVariant
from revold_platform.events.domain import DomainEvent
from revold_notification.domain import Notification


class _FakeWebhookSender:
    def __init__(self, *, fail_urls: set[str] | None = None) -> None:
        self.sent: list[tuple[str, DomainEvent]] = []
        self._fail_urls = fail_urls or set()

    async def send(self, url: str, event: DomainEvent) -> bool:
        self.sent.append((url, event))
        return url not in self._fail_urls


class _FakeProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self._products = {p.sku: p for p in products}

    async def get_product(self, sku: str) -> Product | None:
        return self._products.get(sku)


class _FakeNotificationChannel:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        self.sent.append(notification)


def _make_product(sku: str) -> Product:
    return Product(
        sku=sku,
        name=f"Produto {sku}",
        category=Category(slug="vestidos", name="Vestidos"),
        price=Money(amount=Decimal("99.90")),
        variants=[ProductVariant(sku=f"{sku}-M", size="M", color="Azul", in_stock=True)],
        description=f"Descrição do produto {sku}",
    )


async def test_handle_product_updated_reindexa_o_sku_do_evento(fake_llm, fake_index) -> None:
    repository = _FakeProductRepository([_make_product("P1"), _make_product("P2")])

    ok = await handle_product_updated(
        {"sku": "P1"}, product_repository=repository, llm=fake_llm, index=fake_index
    )

    assert ok is True
    embedding = await fake_llm.embed("qualquer coisa")
    results = await fake_index.search(embedding=embedding, limit=10)
    assert {p.sku for p in results} == {"P1"}


async def test_handle_product_updated_sku_removido_retorna_false(fake_llm, fake_index) -> None:
    repository = _FakeProductRepository([])

    ok = await handle_product_updated(
        {"sku": "SUMIU"}, product_repository=repository, llm=fake_llm, index=fake_index
    )

    assert ok is False


async def test_handle_checkout_created_notifica_novo_checkout() -> None:
    channel = _FakeNotificationChannel()

    await handle_checkout_created(
        {"cart_id": "c1", "summary_text": "1x Camiseta"}, notification_channel=channel
    )

    assert len(channel.sent) == 1
    notification = channel.sent[0]
    assert notification.event_type == "new_checkout"
    assert "c1" in notification.message
    assert "Camiseta" in notification.message


async def test_handle_stock_low_notifica_estoque_baixo() -> None:
    channel = _FakeNotificationChannel()

    await handle_stock_low(
        {"sku": "A", "quantity_available": 2, "threshold": 5}, notification_channel=channel
    )

    assert len(channel.sent) == 1
    notification = channel.sent[0]
    assert notification.event_type == "low_stock"
    assert "A" in notification.message


async def test_forward_to_webhooks_sem_url_nenhuma_nao_chama_o_sender() -> None:
    sender = _FakeWebhookSender()
    event = DomainEvent(name="product.updated", payload={"sku": "CAM-001"})

    result = await forward_to_webhooks(event, webhook_urls=[], sender=sender)

    assert result == {}
    assert sender.sent == []


async def test_forward_to_webhooks_encaminha_para_cada_url_registrada() -> None:
    sender = _FakeWebhookSender()
    event = DomainEvent(name="checkout.created", payload={"cart_id": "c1"})
    urls = ["https://parceiro-a.example.com/hook", "https://parceiro-b.example.com/hook"]

    result = await forward_to_webhooks(event, webhook_urls=urls, sender=sender)

    assert result == {url: True for url in urls}
    assert sender.sent == [(url, event) for url in urls]


async def test_forward_to_webhooks_falha_de_um_destino_nao_afeta_os_demais() -> None:
    urls = ["https://ok.example.com/hook", "https://fora-do-ar.example.com/hook"]
    sender = _FakeWebhookSender(fail_urls={"https://fora-do-ar.example.com/hook"})
    event = DomainEvent(name="stock.low", payload={"sku": "A"})

    result = await forward_to_webhooks(event, webhook_urls=urls, sender=sender)

    assert result == {
        "https://ok.example.com/hook": True,
        "https://fora-do-ar.example.com/hook": False,
    }
