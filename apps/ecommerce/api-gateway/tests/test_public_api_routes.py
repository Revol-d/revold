"""Teste de contrato do router de API pública/parceiro (ADR-0016) — sobe o
app FastAPI de verdade, com ApiKeyAuth/RateLimiter/ProductRepository
trocados por fakes em memória. Autenticação aqui é sempre via header
X-API-Key, nunca cookie de sessão (ver api_gateway.security)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_api_key_auth, get_product_repository, get_rate_limiter
from api_gateway.main import app
from revold_catalog.domain import Category, Money, Product, ProductVariant
from revold_identity.domain import ApiKeyPrincipal


class _FakeProductRepository:
    def __init__(self) -> None:
        self._products = {
            "CAM-001": Product(
                sku="CAM-001",
                name="Camiseta Básica",
                category=Category(slug="camisetas", name="Camisetas"),
                price=Money(Decimal("79.90")),
                variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
            )
        }

    async def list_products(self, *, page, page_size, **_kwargs):
        items = list(self._products.values())
        return items, len(items)


class _FakeApiKeyAuth:
    def __init__(self) -> None:
        self._valid_keys = {"chave-valida": ApiKeyPrincipal(key_id="k1", name="Parceiro ERP")}

    async def resolve(self, raw_key: str) -> ApiKeyPrincipal | None:
        return self._valid_keys.get(raw_key)


class _FakeRateLimiter:
    """Permite tudo por padrão; um teste pode setar `allow_result = False`
    para simular o limite já ter sido atingido."""

    def __init__(self) -> None:
        self.allow_result = True
        self.calls: list[str] = []

    async def allow(self, principal_id: str, *, limit: int, window_seconds: int) -> bool:
        self.calls.append(principal_id)
        return self.allow_result


@pytest.fixture(autouse=True)
def override_dependencies():
    fake_repository = _FakeProductRepository()
    fake_api_key_auth = _FakeApiKeyAuth()
    fake_rate_limiter = _FakeRateLimiter()
    app.dependency_overrides[get_product_repository] = lambda: fake_repository
    app.dependency_overrides[get_api_key_auth] = lambda: fake_api_key_auth
    app.dependency_overrides[get_rate_limiter] = lambda: fake_rate_limiter
    yield fake_rate_limiter
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_sem_header_x_api_key_retorna_401(client: AsyncClient) -> None:
    response = await client.get("/api/public/v1/products")
    assert response.status_code == 401


async def test_com_chave_invalida_retorna_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/public/v1/products", headers={"X-API-Key": "chave-errada"}
    )
    assert response.status_code == 401


async def test_com_chave_valida_lista_produtos(client: AsyncClient) -> None:
    response = await client.get(
        "/api/public/v1/products", headers={"X-API-Key": "chave-valida"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["sku"] == "CAM-001"


async def test_limite_de_requisicoes_excedido_retorna_429(
    client: AsyncClient, override_dependencies: _FakeRateLimiter
) -> None:
    override_dependencies.allow_result = False

    response = await client.get(
        "/api/public/v1/products", headers={"X-API-Key": "chave-valida"}
    )

    assert response.status_code == 429


async def test_rate_limiter_e_chamado_com_o_key_id_do_principal(
    client: AsyncClient, override_dependencies: _FakeRateLimiter
) -> None:
    await client.get("/api/public/v1/products", headers={"X-API-Key": "chave-valida"})

    assert override_dependencies.calls == ["k1"]
