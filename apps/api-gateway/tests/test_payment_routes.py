"""Teste de contrato do router de payments (ADR-0024): sobe o app FastAPI de
verdade, com o repositório de cobranças e o gateway trocados por fakes em
memória — mesma convenção de test_order_routes.py."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from adapters_external.payments.fake_gateway import FakePaymentGateway
from api_gateway.dependencies import (
    get_charge_repository,
    get_inventory_repository,
    get_order_repository,
    get_payment_gateway,
)
from api_gateway.main import app
from core_inventory.domain import StockLevel
from core_orders.domain import Money as OrderMoney
from core_orders.domain import Order, OrderLine, PaymentStatus
from core_payments.domain import Charge


class _FakeOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    async def get(self, order_id: str):
        return self._orders.get(order_id)

    async def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    async def list(self, *, payment_status, page, page_size):
        matching = [
            o for o in self._orders.values() if payment_status is None or o.payment_status == payment_status
        ]
        return matching, len(matching)


class _FakeChargeRepository:
    def __init__(self) -> None:
        self._charges: dict[str, Charge] = {}

    async def get(self, charge_id: str):
        return self._charges.get(charge_id)

    async def get_by_order(self, order_id: str):
        matching = [c for c in self._charges.values() if c.order_id == order_id]
        return matching[-1] if matching else None

    async def get_by_provider_charge_id(self, provider_charge_id: str):
        for charge in self._charges.values():
            if charge.provider_charge_id == provider_charge_id:
                return charge
        return None

    async def save(self, charge: Charge) -> None:
        self._charges[charge.charge_id] = charge


class _FakeInventoryRepository:
    def __init__(self) -> None:
        self._levels: dict[str, StockLevel] = {}

    async def get(self, sku: str):
        return self._levels.get(sku)

    async def save(self, stock_level: StockLevel) -> None:
        self._levels[stock_level.sku] = stock_level


def _order(order_id: str = "o1") -> Order:
    return Order(
        order_id=order_id,
        cart_id="c1",
        lines=(
            OrderLine(
                sku="A",
                product_name="Camiseta",
                variant_label="M",
                unit_price=OrderMoney(Decimal("50")),
                quantity=2,
            ),
        ),
        payment_status=PaymentStatus.PENDING,
        created_at="2026-09-12T10:00:00+00:00",
    )


@pytest.fixture
def fake_order_repository() -> _FakeOrderRepository:
    return _FakeOrderRepository()


@pytest.fixture
def fake_charge_repository() -> _FakeChargeRepository:
    return _FakeChargeRepository()


@pytest.fixture
def fake_gateway() -> FakePaymentGateway:
    return FakePaymentGateway()


@pytest.fixture
def fake_inventory_repository() -> _FakeInventoryRepository:
    return _FakeInventoryRepository()


@pytest.fixture(autouse=True)
def override_dependencies(
    fake_order_repository: _FakeOrderRepository,
    fake_charge_repository: _FakeChargeRepository,
    fake_gateway: FakePaymentGateway,
    fake_inventory_repository: _FakeInventoryRepository,
):
    app.dependency_overrides[get_order_repository] = lambda: fake_order_repository
    app.dependency_overrides[get_charge_repository] = lambda: fake_charge_repository
    app.dependency_overrides[get_payment_gateway] = lambda: fake_gateway
    app.dependency_overrides[get_inventory_repository] = lambda: fake_inventory_repository
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_create_charge_pix_devolve_qr_code(
    client: AsyncClient, fake_order_repository: _FakeOrderRepository
) -> None:
    await fake_order_repository.save(_order())
    response = await client.post("/api/orders/o1/charges", json={"method": "pix"})
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == "o1"
    assert body["pix_qr_code"] is not None
    assert Decimal(str(body["amount"])) == Decimal("100")


async def test_create_charge_pedido_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.post("/api/orders/nao-existe/charges", json={"method": "pix"})
    assert response.status_code == 404


async def test_create_charge_duas_vezes_reaproveita_cobranca_pendente(
    client: AsyncClient, fake_order_repository: _FakeOrderRepository
) -> None:
    await fake_order_repository.save(_order())
    first = await client.post("/api/orders/o1/charges", json={"method": "pix"})
    second = await client.post("/api/orders/o1/charges", json={"method": "pix"})
    assert first.json()["charge_id"] == second.json()["charge_id"]


async def test_get_charge_for_order(
    client: AsyncClient, fake_order_repository: _FakeOrderRepository
) -> None:
    await fake_order_repository.save(_order())
    await client.post("/api/orders/o1/charges", json={"method": "pix"})
    response = await client.get("/api/orders/o1/charges")
    assert response.status_code == 200
    assert response.json()["order_id"] == "o1"


async def test_get_charge_for_order_sem_cobranca_retorna_404(client: AsyncClient) -> None:
    response = await client.get("/api/orders/o1/charges")
    assert response.status_code == 404


async def test_webhook_confirma_pagamento_e_propaga_para_pedido(
    client: AsyncClient,
    fake_order_repository: _FakeOrderRepository,
    fake_charge_repository: _FakeChargeRepository,
    fake_inventory_repository: _FakeInventoryRepository,
) -> None:
    # Pedido de _order() tem uma linha: sku="A", quantity=2 — simula que o
    # checkout já reservou esses 2 (ver api_gateway.routers.cart).
    await fake_inventory_repository.save(StockLevel(sku="A", quantity_on_hand=10, quantity_reserved=2))
    await fake_order_repository.save(_order())
    await client.post("/api/orders/o1/charges", json={"method": "pix"})
    charge = await fake_charge_repository.get_by_order("o1")
    assert charge is not None

    response = await client.post(
        "/api/payments/webhooks/mercado-pago",
        params={"data.id": charge.provider_charge_id},
        headers={"x-signature": "qualquer-coisa-nao-vazia"},
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    order = await fake_order_repository.get("o1")
    assert order is not None
    assert order.payment_status == PaymentStatus.PAID

    reloaded_charge = await fake_charge_repository.get_by_order("o1")
    assert reloaded_charge is not None
    assert reloaded_charge.status.value == "paid"

    stock = await fake_inventory_repository.get("A")
    assert stock is not None
    assert stock.quantity_on_hand == 8
    assert stock.quantity_reserved == 0


async def test_webhook_sem_assinatura_retorna_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/payments/webhooks/mercado-pago",
        params={"data.id": "qualquer"},
        json={},
    )
    assert response.status_code == 401


async def test_webhook_cobranca_desconhecida_devolve_200(client: AsyncClient) -> None:
    response = await client.post(
        "/api/payments/webhooks/mercado-pago",
        params={"data.id": "nao-existe"},
        headers={"x-signature": "qualquer-coisa"},
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "unknown_charge"


async def test_webhook_sem_data_id_e_ignorado(client: AsyncClient) -> None:
    response = await client.post(
        "/api/payments/webhooks/mercado-pago",
        headers={"x-signature": "qualquer-coisa"},
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
