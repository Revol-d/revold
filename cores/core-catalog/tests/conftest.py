from __future__ import annotations

from decimal import Decimal

import pytest

from core_catalog.domain import Category, Money, Product, ProductVariant


class FakeProductRepository:
    """Adapter fake em memória — usado só em teste, nunca em produção.

    Implementa a mesma porta (core_catalog.ports.ProductRepository) que o
    adapter real de Postgres implementa, por estrutura (Protocol), sem
    herança formal.
    """

    def __init__(self, products: list[Product]) -> None:
        self._products = {p.sku: p for p in products}
        self._categories: dict[str, Category] = {p.category.slug: p.category for p in products}

    async def list_categories(self) -> list[Category]:
        return list(self._categories.values())

    async def get_category(self, slug: str) -> Category | None:
        return self._categories.get(slug)

    async def save_category(self, category: Category) -> None:
        self._categories[category.slug] = category

    async def list_products(
        self, *, category_slug: str | None, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        items = list(self._products.values())
        if category_slug is not None:
            items = [p for p in items if p.category.slug == category_slug]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    async def get_product(self, sku: str) -> Product | None:
        return self._products.get(sku)

    async def save_product(self, product: Product) -> None:
        self._products[product.sku] = product

    async def find_variant_owner(self, variant_sku: str) -> str | None:
        for product in self._products.values():
            if any(v.sku == variant_sku for v in product.variants):
                return product.sku
        return None


@pytest.fixture
def sample_products() -> list[Product]:
    camisetas = Category(slug="camisetas", name="Camisetas")
    calcas = Category(slug="calcas", name="Calças")
    return [
        Product(
            sku="CAM-001",
            name="Camiseta Básica",
            category=camisetas,
            price=Money(Decimal("79.90")),
            variants=[
                ProductVariant(sku="CAM-001-P-BR", size="P", color="Branco", in_stock=True),
                ProductVariant(sku="CAM-001-M-BR", size="M", color="Branco", in_stock=False),
            ],
            images=["https://example.com/cam-001.jpg"],
        ),
        Product(
            sku="CAL-001",
            name="Calça Jeans",
            category=calcas,
            price=Money(Decimal("199.90")),
            variants=[
                ProductVariant(sku="CAL-001-38", size="38", color="Azul", in_stock=True),
            ],
            images=["https://example.com/cal-001.jpg"],
        ),
    ]


@pytest.fixture
def fake_repository(sample_products: list[Product]) -> FakeProductRepository:
    return FakeProductRepository(sample_products)
