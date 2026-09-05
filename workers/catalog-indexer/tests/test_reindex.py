from __future__ import annotations

from decimal import Decimal

from catalog_indexer.reindex import reindex_all_products
from core_ai_assistant.use_cases import IndexProduct
from core_catalog.domain import Category, Money, Product, ProductVariant


class _FakeProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self._products = products

    async def list_categories(self) -> list[Category]:
        return []

    async def list_products(
        self, *, category_slug: str | None, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        start = (page - 1) * page_size
        end = start + page_size
        return self._products[start:end], len(self._products)

    async def get_product(self, sku: str) -> Product | None:
        return next((p for p in self._products if p.sku == sku), None)


def _make_product(sku: str) -> Product:
    return Product(
        sku=sku,
        name=f"Produto {sku}",
        category=Category(slug="vestidos", name="Vestidos"),
        price=Money(amount=Decimal("99.90")),
        variants=[ProductVariant(sku=f"{sku}-M", size="M", color="Azul", in_stock=True)],
        description=f"Descrição do produto {sku}",
    )


async def test_reindex_all_products_indexa_tudo_paginando(fake_llm, fake_index) -> None:
    products = [_make_product(f"P{i}") for i in range(5)]
    repository = _FakeProductRepository(products)
    index_product = IndexProduct(fake_llm, fake_index)

    count = await reindex_all_products(repository, index_product, page_size=2)

    assert count == 5
    embedding = await fake_llm.embed("qualquer coisa")
    results = await fake_index.search(embedding=embedding, limit=10)
    assert {p.sku for p in results} == {p.sku for p in products}


async def test_reindex_all_products_catalogo_vazio_retorna_zero(fake_llm, fake_index) -> None:
    repository = _FakeProductRepository([])
    index_product = IndexProduct(fake_llm, fake_index)

    count = await reindex_all_products(repository, index_product)

    assert count == 0
