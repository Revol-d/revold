"""Casos de uso do core-catalog. Orquestram a porta ProductRepository."""
from __future__ import annotations

from dataclasses import dataclass

from core_catalog.domain import (
    Category,
    CategoryNotFound,
    DuplicateSku,
    Money,
    Product,
    ProductNotFound,
    ProductVariant,
)
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


class CreateCategory:
    """Cria (ou atualiza, se o slug já existir) uma categoria — uso
    administrativo (RBAC STAFF/ADMIN aplicado no api-gateway)."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self, *, slug: str, name: str) -> Category:
        category = Category(slug=slug, name=name)
        await self._repository.save_category(category)
        return category


class CreateProduct:
    """Cria um produto novo no catálogo — uso administrativo (RBAC
    STAFF/ADMIN aplicado no api-gateway). Não permite recriar um SKU já
    existente (use um caso de uso de atualização, ainda não implementado,
    para isso)."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        sku: str,
        name: str,
        category_slug: str,
        price: Money,
        variants: list[ProductVariant],
        description: str = "",
        images: list[str] | None = None,
        original_price: Money | None = None,
    ) -> Product:
        category = await self._repository.get_category(category_slug)
        if category is None:
            raise CategoryNotFound(category_slug)

        if await self._repository.get_product(sku) is not None:
            raise DuplicateSku(sku)

        product = Product(
            sku=sku,
            name=name,
            category=category,
            price=price,
            variants=variants,
            images=images or [],
            description=description,
            original_price=original_price,
        )
        await self._repository.save_product(product)
        return product
