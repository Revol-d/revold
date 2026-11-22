"""Teste de contrato do router de inventory: sobe o app FastAPI de verdade,
com o repositório de estoque trocado por um fake em memória."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import (
    get_event_publisher,
    get_inventory_repository,
    get_low_stock_threshold,
)
from api_gateway.main import app
from api_gateway.security import get_current_user
from revold_platform.events.domain import DomainEvent
from revold_identity.domain import AuthenticatedUser, Role
from revold_inventory.domain import StockLevel

_STAFF_USER = AuthenticatedUser(
    external_id="staff-1",
    provider="dev",
    email="staff@example.com",
    name="Staff",
    roles=(Role.STAFF,),
)


class _FakeInventoryRepository:
    def __init__(self) -> None:
        self._levels: dict[str, StockLevel] = {}

    async def get(self, sku: str):
        return self._levels.get(sku)

    async def save(self, stock_level: StockLevel) -> None:
        self._levels[stock_level.sku] = stock_level


class _FakeEventPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)


@pytest.fixture
def fake_event_publisher() -> _FakeEventPublisher:
    return _FakeEventPublisher()


@pytest.fixture(autouse=True)
def override_dependencies(fake_event_publisher: _FakeEventPublisher):
    fake_repo = _FakeInventoryRepository()
    app.dependency_overrides[get_inventory_repository] = lambda: fake_repo
    app.dependency_overrides[get_event_publisher] = lambda: fake_event_publisher
    # get_low_stock_threshold agora lê `store-settings` via Azure SQL
    # (ADR-0019) — sobrescrito aqui com o mesmo valor padrão de antes (5)
    # para não fazer este teste de unidade abrir uma sessão de banco de
    # verdade (mesmo cuidado de test_metrics_endpoint.py: um novo event
    # loop por teste do pytest-asyncio bate com o engine async singleton).
    app.dependency_overrides[get_low_stock_threshold] = lambda: 5
    # Endpoints administrativos (receive/reserve/release) exigem STAFF/ADMIN
    # (ADR-0010) — os testes de contrato aqui autenticam como staff; os
    # testes de RBAC em si (401/403) ficam em test_inventory_rbac.py.
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_get_stock_level_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.get("/api/inventory/NAO-EXISTE")
    assert response.status_code == 404


async def test_receive_cria_nivel_de_estoque(client: AsyncClient) -> None:
    response = await client.post("/api/inventory/A/receive", json={"quantity": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["quantity_on_hand"] == 10
    assert body["quantity_available"] == 10


async def test_get_stock_level_apos_receive(client: AsyncClient) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    response = await client.get("/api/inventory/A")
    assert response.status_code == 200
    assert response.json()["quantity_on_hand"] == 10


async def test_reserve_reduz_disponibilidade(client: AsyncClient) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    response = await client.post("/api/inventory/A/reserve", json={"quantity": 4})
    assert response.status_code == 200
    body = response.json()
    assert body["quantity_reserved"] == 4
    assert body["quantity_available"] == 6


async def test_reserve_sku_inexistente_retorna_404(client: AsyncClient) -> None:
    response = await client.post("/api/inventory/NAO-EXISTE/reserve", json={"quantity": 1})
    assert response.status_code == 404


async def test_reserve_alem_do_disponivel_retorna_422(client: AsyncClient) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 2})
    response = await client.post("/api/inventory/A/reserve", json={"quantity": 5})
    assert response.status_code == 422


async def test_release_devolve_disponibilidade(client: AsyncClient) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    await client.post("/api/inventory/A/reserve", json={"quantity": 4})
    response = await client.post("/api/inventory/A/release", json={"quantity": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["quantity_reserved"] == 3
    assert body["quantity_available"] == 7


async def test_release_alem_do_reservado_retorna_422(client: AsyncClient) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    await client.post("/api/inventory/A/reserve", json={"quantity": 2})
    response = await client.post("/api/inventory/A/release", json={"quantity": 5})
    assert response.status_code == 422


async def test_reserve_com_quantidade_zero_retorna_erro_de_validacao(client: AsyncClient) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    response = await client.post("/api/inventory/A/reserve", json={"quantity": 0})
    assert response.status_code == 422


async def test_reserve_abaixo_do_limiar_publica_evento_stock_low(
    client: AsyncClient, fake_event_publisher: _FakeEventPublisher
) -> None:
    # limiar padrão (LOW_STOCK_THRESHOLD) é 5
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    response = await client.post("/api/inventory/A/reserve", json={"quantity": 8})
    assert response.status_code == 200
    assert len(fake_event_publisher.published) == 1
    event = fake_event_publisher.published[0]
    assert event.name == "stock.low"
    assert event.payload["sku"] == "A"


async def test_reserve_acima_do_limiar_nao_publica_evento(
    client: AsyncClient, fake_event_publisher: _FakeEventPublisher
) -> None:
    await client.post("/api/inventory/A/receive", json={"quantity": 10})
    response = await client.post("/api/inventory/A/reserve", json={"quantity": 2})
    assert response.status_code == 200
    assert fake_event_publisher.published == []
