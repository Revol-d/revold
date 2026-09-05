"""Teste de contrato leve do router de catalog: sobe o app FastAPI de verdade,
mas troca o repositório real pelo fake em memória via override de dependência
do FastAPI — não precisa de Postgres para validar o contrato HTTP.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_product_repository
from api_gateway.main import app
from core_catalog.domain import Category, Money, Product, ProductVariant


class _FakeRepository:
    def __init__(self) -> None:
        self._products = {
            "CAM-001": Product(
                sku="CAM-001",
                name="Camiseta Básica",
                category=Category(slug="camisetas", name="Camisetas"),
                price=Money(Decimal("79.90")),
                variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
                images=["https://example.com/cam-001.jpg"],
            )
        }

    async def list_categories(self):
        return [p.category for p in self._products.values()]

    async def list_products(self, *, category_slug, page, page_size):
        items = list(self._products.values())
        if category_slug:
            items = [p for p in items if p.category.slug == category_slug]
        return items, len(items)

    async def get_product(self, sku):
        return self._products.get(sku)


@pytest.fixture(autouse=True)
def override_repository():
    app.dependency_overrides[get_product_repository] = lambda: _FakeRepository()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_products(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["sku"] == "CAM-001"


async def test_get_product_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products/NAO-EXISTE")
    assert response.status_code == 404


async def test_get_product_found(client: AsyncClient) -> None:
    response = await client.get("/api/catalog/products/CAM-001")
    assert response.status_code == 200
    assert response.json()["name"] == "Camiseta Básica"
