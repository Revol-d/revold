"""Teste de contrato do router de store-settings (ADR-0019): sobe o app
FastAPI de verdade, com o repositório trocado por um fake em memória."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_store_settings_repository
from api_gateway.main import app
from api_gateway.security import get_current_user
from revold_identity.domain import AuthenticatedUser, Role
from revold_store_settings.domain import StoreSettings


class _FakeStoreSettingsRepository:
    def __init__(self) -> None:
        self._settings: StoreSettings | None = None

    async def get(self) -> StoreSettings | None:
        return self._settings

    async def save(self, settings: StoreSettings) -> None:
        self._settings = settings


_ADMIN_USER = AuthenticatedUser(
    external_id="admin-1", provider="dev", email="admin@example.com", name="Admin",
    roles=(Role.ADMIN,),
)
_STAFF_USER = AuthenticatedUser(
    external_id="staff-1", provider="dev", email="staff@example.com", name="Staff",
    roles=(Role.STAFF,),
)


@pytest.fixture
def fake_repository() -> _FakeStoreSettingsRepository:
    return _FakeStoreSettingsRepository()


@pytest.fixture(autouse=True)
def override_dependencies(fake_repository: _FakeStoreSettingsRepository):
    app.dependency_overrides[get_store_settings_repository] = lambda: fake_repository
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_get_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.get("/api/store-settings")
    assert response.status_code == 401


async def test_get_com_papel_staff_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.get("/api/store-settings")
    assert response.status_code == 403


async def test_get_com_papel_admin_e_nada_configurado_devolve_registro_vazio(
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER
    response = await client.get("/api/store-settings")
    assert response.status_code == 200
    body = response.json()
    assert body["cnpj"] == ""
    assert body["store_name"] == ""
    assert body["low_stock_threshold"] == 5  # LOW_STOCK_THRESHOLD (env) não setado no teste


async def test_put_com_papel_admin_atualiza_e_persiste(
    client: AsyncClient, fake_repository: _FakeStoreSettingsRepository
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER

    response = await client.put(
        "/api/store-settings",
        json={
            "cnpj": "12.345.678/0001-95",
            "store_name": "Nick Roupas",
            "contact_email": "contato@nick.com.br",
            "contact_phone": "+55 11 90000-0000",
            "store_address": "Rua das Flores, 123",
            "low_stock_threshold": 8,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["store_name"] == "Nick Roupas"
    assert body["low_stock_threshold"] == 8

    persisted = await fake_repository.get()
    assert persisted is not None
    assert persisted.store_name == "Nick Roupas"


async def test_put_com_papel_staff_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.put("/api/store-settings", json={"store_name": "Nick Roupas"})
    assert response.status_code == 403


async def test_put_altera_so_o_campo_informado(
    client: AsyncClient, fake_repository: _FakeStoreSettingsRepository
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER

    await client.put("/api/store-settings", json={"store_name": "Nick Roupas"})
    response = await client.put("/api/store-settings", json={"contact_phone": "+55 11 91234-5678"})

    assert response.status_code == 200
    body = response.json()
    assert body["store_name"] == "Nick Roupas"
    assert body["contact_phone"] == "+55 11 91234-5678"


async def test_put_com_cnpj_invalido_retorna_422(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER
    response = await client.put("/api/store-settings", json={"cnpj": "123"})
    assert response.status_code == 422
