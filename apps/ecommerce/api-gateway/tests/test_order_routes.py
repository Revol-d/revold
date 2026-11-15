"""Teste de contrato do router de orders (ADR-0023): sobe o app FastAPI de
verdade, com o repositório de pedidos trocado por um fake em memória —
mesma convenção de test_inventory_routes.py."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_inventory_repository, get_order_repository
from api_gateway.main import app
from api_gateway.security import get_current_user
from revold_identity.domain import AuthenticatedUser, Role
from revold_inventory.domain import StockLevel
from revold_orders.domain import Money, Order, OrderLine, PaymentStatus

_STAFF_USER = AuthenticatedUser(
    external_id="staff-1", provider="dev", email="staff@example.com", name="Staff", roles=(Role.STAFF,)
)
_CUSTOMER_USER = AuthenticatedUser(
    external_id="cust-1",
    provider="dev",
    email="cliente@example.com",
    name="Cliente",
    roles=(Role.CUSTOMER,),
)


class _FakeOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    async def get(self, order_id: str):
        return self._orders.get(order_id)

    async def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    async def list(self, *, payment_status: PaymentStatus | None, page: int, page_size: int):
        matching = [
            o for o in self._orders.values() if payment_status is None or o.payment_status == payment_status
        ]
        return matching, len(matching)


class _FakeInventoryRepository:
    def __init__(self) -> None:
        self._levels: dict[str, StockLevel] = {}

    async def get(self, sku: str):
        return self._levels.get(sku)

    async def save(self, stock_level: StockLevel) -> None:
        self._levels[stock_level.sku] = stock_level


def _order(order_id: str = "o1", payment_status: PaymentStatus = PaymentStatus.PENDING) -> Order:
    return Order(
        order_id=order_id,
        cart_id="c1",
        lines=(
            OrderLine(
                sku="A", product_name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2
            ),
        ),
        payment_status=payment_status,
        created_at="2026-09-12T10:00:00+00:00",
    )


@pytest.fixture
def fake_repository() -> _FakeOrderRepository:
    return _FakeOrderRepository()


@pytest.fixture
def fake_inventory_repository() -> _FakeInventoryRepository:
    return _FakeInventoryRepository()


@pytest.fixture(autouse=True)
def override_dependencies(
    fake_repository: _FakeOrderRepository, fake_inventory_repository: _FakeInventoryRepository
):
    app.dependency_overrides[get_order_repository] = lambda: fake_repository
    app.dependency_overrides[get_inventory_repository] = lambda: fake_inventory_repository
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_get_order_sem_rbac(client: AsyncClient, fake_repository: _FakeOrderRepository) -> None:
    # get_current_user segue sobrescrito (autouse), mas o endpoint em si não
    # exige nenhum papel — order_id funciona como token de capacidade.
    await fake_repository.save(_order())
    response = await client.get("/api/orders/o1")
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "o1"
    assert body["total"] == "100.00" or Decimal(str(body["total"])) == Decimal("100")


async def test_get_order_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.get("/api/orders/nao-existe")
    assert response.status_code == 404


async def test_list_orders_exige_staff_ou_admin(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.get("/api/orders")
    assert response.status_code == 403


async def test_list_orders_filtra_por_payment_status(
    client: AsyncClient, fake_repository: _FakeOrderRepository
) -> None:
    await fake_repository.save(_order("o1", PaymentStatus.PENDING))
    await fake_repository.save(_order("o2", PaymentStatus.PAID))

    response = await client.get("/api/orders", params={"payment_status": "paid"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["order_id"] == "o2"


async def test_mark_paid(client: AsyncClient, fake_repository: _FakeOrderRepository) -> None:
    await fake_repository.save(_order())
    response = await client.patch("/api/orders/o1/payment-status", json={"action": "mark_paid"})
    assert response.status_code == 200
    assert response.json()["payment_status"] == "paid"


async def test_mark_paid_confirma_baixa_definitiva_de_estoque(
    client: AsyncClient,
    fake_repository: _FakeOrderRepository,
    fake_inventory_repository: _FakeInventoryRepository,
) -> None:
    # Pedido de _order() tem uma linha: sku="A", quantity=2 (ver topo do
    # arquivo) — simula que o checkout já reservou esses 2.
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=10, quantity_reserved=2))
    await fake_repository.save(_order())

    response = await client.patch("/api/orders/o1/payment-status", json={"action": "mark_paid"})
    assert response.status_code == 200

    stock = await fake_inventory_repository.get("A")
    assert stock is not None
    assert stock.quantity_on_hand == 8
    assert stock.quantity_reserved == 0


async def test_mark_paid_sem_estoque_registrado_nao_quebra_a_confirmacao(
    client: AsyncClient, fake_repository: _FakeOrderRepository
) -> None:
    # Sem nenhum StockLevel salvo para o sku da linha — FulfillReservedStock
    # levantaria StockLevelNotFound, mas isso não deve impedir o pagamento
    # de ser confirmado (ver revold_ecommerce.application.stock.fulfill_order_stock).
    await fake_repository.save(_order())
    response = await client.patch("/api/orders/o1/payment-status", json={"action": "mark_paid"})
    assert response.status_code == 200
    assert response.json()["payment_status"] == "paid"


async def test_mark_paid_pedido_ja_pago_retorna_422(
    client: AsyncClient, fake_repository: _FakeOrderRepository
) -> None:
    await fake_repository.save(_order("o1", PaymentStatus.PAID))
    response = await client.patch("/api/orders/o1/payment-status", json={"action": "mark_paid"})
    assert response.status_code == 422


async def test_mark_shipped_exige_pagamento_confirmado(
    client: AsyncClient, fake_repository: _FakeOrderRepository
) -> None:
    await fake_repository.save(_order())
    response = await client.patch("/api/orders/o1/fulfillment-status", json={"action": "mark_shipped"})
    assert response.status_code == 422


async def test_fluxo_pago_enviado_entregue(
    client: AsyncClient, fake_repository: _FakeOrderRepository
) -> None:
    await fake_repository.save(_order())
    await client.patch("/api/orders/o1/payment-status", json={"action": "mark_paid"})
    shipped = await client.patch("/api/orders/o1/fulfillment-status", json={"action": "mark_shipped"})
    assert shipped.json()["fulfillment_status"] == "shipped"
    delivered = await client.patch("/api/orders/o1/fulfillment-status", json={"action": "mark_delivered"})
    assert delivered.json()["fulfillment_status"] == "delivered"


async def test_update_payment_status_exige_staff_ou_admin(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.patch("/api/orders/o1/payment-status", json={"action": "mark_paid"})
    assert response.status_code == 403
