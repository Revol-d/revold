"""Teste de contrato do router de cart: sobe o app FastAPI de verdade, com o
repositório de carrinho trocado por um fake em memória, o repositório de
estoque trocado por um fake em memória e o checkout trocado por um fake que
não depende de NICK_WHATSAPP_NUMBER configurado."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import (
    get_cart_repository,
    get_checkout_handoff,
    get_event_publisher,
    get_inventory_repository,
    get_low_stock_threshold,
)
from api_gateway.main import app
from core_cart.domain import Cart
from core_events.domain import DomainEvent
from core_inventory.domain import StockLevel


class _FakeCartRepository:
    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}

    async def get(self, cart_id: str):
        return self._carts.get(cart_id)

    async def save(self, cart: Cart) -> None:
        self._carts[cart.cart_id] = cart

    async def delete(self, cart_id: str) -> None:
        self._carts.pop(cart_id, None)


class _FakeInventoryRepository:
    def __init__(self) -> None:
        self._levels: dict[str, StockLevel] = {}

    async def get(self, sku: str):
        return self._levels.get(sku)

    async def save(self, stock_level: StockLevel) -> None:
        self._levels[stock_level.sku] = stock_level


class _FakeCheckoutHandoff:
    provider_name = "fake"

    def build_handoff(self, summary) -> str:
        return f"https://fake.test/checkout?total={summary.total_amount}"


class _FailingCheckoutHandoff:
    provider_name = "fake"

    def build_handoff(self, summary) -> str:
        raise ValueError("NICK_WHATSAPP_NUMBER não configurado")


class _FakeEventPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)


@pytest.fixture
def fake_inventory_repository() -> _FakeInventoryRepository:
    return _FakeInventoryRepository()


@pytest.fixture
def fake_event_publisher() -> _FakeEventPublisher:
    return _FakeEventPublisher()


@pytest.fixture(autouse=True)
def override_dependencies(
    fake_inventory_repository: _FakeInventoryRepository,
    fake_event_publisher: _FakeEventPublisher,
):
    fake_repo = _FakeCartRepository()
    app.dependency_overrides[get_cart_repository] = lambda: fake_repo
    app.dependency_overrides[get_inventory_repository] = lambda: fake_inventory_repository
    app.dependency_overrides[get_checkout_handoff] = lambda: _FakeCheckoutHandoff()
    app.dependency_overrides[get_event_publisher] = lambda: fake_event_publisher
    # get_low_stock_threshold agora lê core-store-settings via Postgres
    # (ADR-0019) — sobrescrito aqui com o mesmo valor padrão de antes (5)
    # para não fazer este teste de unidade abrir uma sessão de banco de
    # verdade (mesmo cuidado de test_metrics_endpoint.py: um novo event
    # loop por teste do pytest-asyncio bate com o engine async singleton).
    app.dependency_overrides[get_low_stock_threshold] = lambda: 5
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_get_cart_cria_vazio(client: AsyncClient) -> None:
    response = await client.get("/api/cart/c1")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert Decimal(str(body["total"])) == Decimal("0")


async def test_add_item_e_get_cart(client: AsyncClient) -> None:
    response = await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "79.90", "quantity": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["quantity"] == 2
    assert Decimal(str(body["total"])) == Decimal("159.80")


async def test_add_item_sem_estoque_cadastrado_retorna_available_quantity_null(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/cart/c1/items",
        json={"sku": "NAO-RASTREADO", "name": "Item", "variant_label": "U", "unit_price": "10", "quantity": 1},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["available_quantity"] is None


async def test_get_cart_reflete_disponibilidade_de_estoque(
    client: AsyncClient, fake_inventory_repository: _FakeInventoryRepository
) -> None:
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=10, quantity_reserved=3))
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "10", "quantity": 1},
    )
    response = await client.get("/api/cart/c1")
    assert response.status_code == 200
    assert response.json()["items"][0]["available_quantity"] == 7


async def test_add_item_nao_bloqueia_mesmo_sem_estoque_disponivel(
    client: AsyncClient, fake_inventory_repository: _FakeInventoryRepository
) -> None:
    """Adicionar ao carrinho é só uma intenção — não reserva nada. A
    reserva de verdade (e o bloqueio por falta de estoque) só acontece no
    checkout (ver test_checkout_com_estoque_insuficiente_retorna_422)."""
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=0))
    response = await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "10", "quantity": 5},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["available_quantity"] == 0


async def test_update_item_quantity(client: AsyncClient) -> None:
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "10", "quantity": 1},
    )
    response = await client.patch("/api/cart/c1/items/A", json={"quantity": 3})
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 3


async def test_update_item_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.patch("/api/cart/c1/items/NAO-EXISTE", json={"quantity": 1})
    assert response.status_code == 404


async def test_remove_item(client: AsyncClient) -> None:
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "10", "quantity": 1},
    )
    response = await client.delete("/api/cart/c1/items/A")
    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_checkout_com_carrinho_vazio_retorna_422(client: AsyncClient) -> None:
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 422


async def test_checkout_com_itens(client: AsyncClient) -> None:
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "fake"
    assert "100" in body["handoff_url"]


async def test_clear_cart(client: AsyncClient) -> None:
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "10", "quantity": 1},
    )
    response = await client.delete("/api/cart/c1")
    assert response.status_code == 204
    reloaded = await client.get("/api/cart/c1")
    assert reloaded.json()["items"] == []


async def test_checkout_reserva_estoque_quando_disponivel(
    client: AsyncClient, fake_inventory_repository: _FakeInventoryRepository
) -> None:
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=5))
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 200
    stock = await fake_inventory_repository.get("A")
    assert stock is not None
    assert stock.quantity_reserved == 2
    assert stock.quantity_available == 3


async def test_checkout_com_estoque_insuficiente_retorna_422(
    client: AsyncClient, fake_inventory_repository: _FakeInventoryRepository
) -> None:
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=1))
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 422
    stock = await fake_inventory_repository.get("A")
    assert stock is not None
    assert stock.quantity_reserved == 0  # nada deve ficar reservado


async def test_checkout_libera_reservas_parciais_quando_item_seguinte_falha(
    client: AsyncClient, fake_inventory_repository: _FakeInventoryRepository
) -> None:
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=5))
    await fake_inventory_repository.save(StockLevel(sku="B", quantity_on_hand=1))
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "B", "name": "Calça", "variant_label": "G", "unit_price": "50", "quantity": 5},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 422
    stock_a = await fake_inventory_repository.get("A")
    assert stock_a is not None
    assert stock_a.quantity_reserved == 0  # reserva do item A foi desfeita


async def test_checkout_ignora_sku_sem_controle_de_estoque(client: AsyncClient) -> None:
    """SKU sem StockLevel cadastrado (core-inventory ainda não adotado para
    ele) não deve bloquear o checkout — comportamento anterior à introdução
    de core-inventory."""
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "NAO-RASTREADO", "name": "Item", "variant_label": "U", "unit_price": "10", "quantity": 1},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 200


async def test_checkout_libera_reserva_quando_handoff_falha(
    client: AsyncClient, fake_inventory_repository: _FakeInventoryRepository
) -> None:
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=5))
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    app.dependency_overrides[get_checkout_handoff] = lambda: _FailingCheckoutHandoff()
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 422
    stock = await fake_inventory_repository.get("A")
    assert stock is not None
    assert stock.quantity_reserved == 0  # reserva foi desfeita, não fica presa


async def test_checkout_bem_sucedido_publica_evento_checkout_created(
    client: AsyncClient, fake_event_publisher: _FakeEventPublisher
) -> None:
    """A notificação de verdade pra Nick roda assíncrona, disparada por
    quem consome esse evento (ver workers/event-worker, ADR-0013) — aqui só
    verificamos que o api-gateway publicou o evento certo, não que a
    notificação foi enviada (isso é responsabilidade do worker, testada em
    workers/event-worker/tests)."""
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 200
    checkout_events = [e for e in fake_event_publisher.published if e.name == "checkout.created"]
    assert len(checkout_events) == 1
    assert checkout_events[0].payload["cart_id"] == "c1"
    assert "Camiseta" in checkout_events[0].payload["summary_text"]


async def test_checkout_com_erro_nao_publica_evento(
    client: AsyncClient, fake_event_publisher: _FakeEventPublisher
) -> None:
    response = await client.post("/api/cart/c1/checkout")  # carrinho vazio -> 422
    assert response.status_code == 422
    assert fake_event_publisher.published == []


async def test_checkout_reserva_estoque_baixo_publica_evento_stock_low(
    client: AsyncClient,
    fake_inventory_repository: _FakeInventoryRepository,
    fake_event_publisher: _FakeEventPublisher,
) -> None:
    # limiar padrão (LOW_STOCK_THRESHOLD) é 5; deixar 2 disponíveis dispara o evento
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=4))
    await client.post(
        "/api/cart/c1/items",
        json={"sku": "A", "name": "Camiseta", "variant_label": "M", "unit_price": "50", "quantity": 2},
    )
    response = await client.post("/api/cart/c1/checkout")
    assert response.status_code == 200
    event_names = [e.name for e in fake_event_publisher.published]
    assert "stock.low" in event_names
    stock_low_event = next(e for e in fake_event_publisher.published if e.name == "stock.low")
    assert stock_low_event.payload["sku"] == "A"
