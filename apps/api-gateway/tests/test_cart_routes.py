"""Teste de contrato do router de cart: sobe o app FastAPI de verdade, com o
repositório de carrinho trocado por um fake em memória e o checkout trocado
por um fake que não depende de NICK_WHATSAPP_NUMBER configurado."""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_cart_repository, get_checkout_handoff
from api_gateway.main import app
from core_cart.domain import Cart


class _FakeCartRepository:
    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}

    async def get(self, cart_id: str):
        return self._carts.get(cart_id)

    async def save(self, cart: Cart) -> None:
        self._carts[cart.cart_id] = cart

    async def delete(self, cart_id: str) -> None:
        self._carts.pop(cart_id, None)


class _FakeCheckoutHandoff:
    provider_name = "fake"

    def build_handoff(self, summary) -> str:
        return f"https://fake.test/checkout?total={summary.total_amount}"


@pytest.fixture(autouse=True)
def override_dependencies():
    fake_repo = _FakeCartRepository()
    app.dependency_overrides[get_cart_repository] = lambda: fake_repo
    app.dependency_overrides[get_checkout_handoff] = lambda: _FakeCheckoutHandoff()
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
