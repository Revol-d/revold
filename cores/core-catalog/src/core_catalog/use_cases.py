"""Casos de uso do core-catalog. Orquestram a porta ProductRepository."""
from __future__ import annotations

from dataclasses import dataclass

from core_catalog.domain import Category, Product, ProductNotFound
from core_catalog.ports import ProductRepository


@dataclass(slots=True)
class ProductPageResult:
    items: list[Product]
    page: int
    page_size: int
    total: int


class ListCategories:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[Category]:
        return await self._repository.list_categories()


class ListProducts:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(
        self, *, category_slug: str | None = None, page: int = 1, page_size: int = 24
    ) -> ProductPageResult:
        if page < 1:
            raise ValueError("page deve ser >= 1")
        if not (1 <= page_size <= 100):
            raise ValueError("page_size deve estar entre 1 e 100")
        items, total = await self._repository.list_products(
            category_slug=category_slug, page=page, page_size=page_size
        )
        return ProductPageResult(items=items, page=page, page_size=page_size, total=total)


class GetProduct:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str) -> Product:
        product = await self._repository.get_product(sku)
        if product is None:
            raise ProductNotFound(sku)
        return product
