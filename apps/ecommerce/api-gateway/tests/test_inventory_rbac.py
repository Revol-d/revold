"""Testes de RBAC (ADR-0010) nos endpoints administrativos de estoque:
receive/reserve/release exigem papel STAFF ou ADMIN; get_stock_level
continua público (leitura)."""
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
from revold_identity.domain import AuthenticatedUser, Role
from revold_inventory.domain import StockLevel


class _FakeInventoryRepository:
    def __init__(self) -> None:
        self._levels: dict[str, StockLevel] = {}

    async def get(self, sku: str):
        return self._levels.get(sku)

    async def save(self, stock_level: StockLevel) -> None:
        self._levels[stock_level.sku] = stock_level


class _FakeEventPublisher:
    async def publish(self, event) -> None:
        pass


_CUSTOMER_USER = AuthenticatedUser(
    external_id="cust-1", provider="dev", email="cliente@example.com", name="Cliente",
    roles=(Role.CUSTOMER,),
)
_STAFF_USER = AuthenticatedUser(
    external_id="staff-1", provider="dev", email="staff@example.com", name="Staff",
    roles=(Role.STAFF,),
)


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_inventory_repository] = lambda: _FakeInventoryRepository()
    app.dependency_overrides[get_event_publisher] = lambda: _FakeEventPublisher()
    # get_low_stock_threshold agora lê `store-settings` via Azure SQL
    # (ADR-0019) e é declarado antes da checagem de RBAC em reserve_stock —
    # sobrescrito aqui para nenhum teste de 401/403 chegar a abrir uma
    # sessão de banco de verdade antes da checagem de autenticação/papel.
    app.dependency_overrides[get_low_stock_threshold] = lambda: 5
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_receive_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post("/api/inventory/A/receive", json={"quantity": 10})
    assert response.status_code == 401


async def test_receive_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.post("/api/inventory/A/receive", json={"quantity": 10})
    assert response.status_code == 403


async def test_receive_com_papel_staff_retorna_200(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post("/api/inventory/A/receive", json={"quantity": 10})
    assert response.status_code == 200


async def test_reserve_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post("/api/inventory/A/reserve", json={"quantity": 1})
    assert response.status_code == 401


async def test_release_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post("/api/inventory/A/release", json={"quantity": 1})
    assert response.status_code == 401


async def test_get_stock_level_continua_publico_sem_autenticacao(client: AsyncClient) -> None:
    response = await client.get("/api/inventory/NAO-EXISTE")
    # 404 (não achou o SKU), não 401 — leitura não exige sessão.
    assert response.status_code == 404
