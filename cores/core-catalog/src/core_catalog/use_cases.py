"""Casos de uso do core-catalog. Orquestram a porta ProductRepository."""
from __future__ import annotations

from dataclasses import dataclass

from core_catalog.domain import (
    Category,
    CategoryNotFound,
    DuplicateSku,
    DuplicateVariantSku,
    Money,
    Product,
    ProductNotFound,
    ProductVariant,
)
from core_catalog.ports import ProductRepository

VALID_SORTS = frozenset({"relevance", "price_asc", "price_desc"})


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
        self,
        *,
        category_slug: str | None = None,
        search_query: str | None = None,
        sort: str = "relevance",
        page: int = 1,
        page_size: int = 24,
    ) -> ProductPageResult:
        if page < 1:
            raise ValueError("page deve ser >= 1")
        if not (1 <= page_size <= 100):
            raise ValueError("page_size deve estar entre 1 e 100")
        if sort not in VALID_SORTS:
            raise ValueError(f"sort deve ser um de {sorted(VALID_SORTS)}")
        items, total = await self._repository.list_products(
            category_slug=category_slug,
            search_query=search_query,
            sort=sort,
            page=page,
            page_size=page_size,
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
    existente (use UpdateProduct/AddProductVariant para mexer num produto
    que já existe)."""

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

        for variant in variants:
            if await self._repository.find_variant_owner(variant.sku) is not None:
                raise DuplicateVariantSku(variant.sku)

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


class UpdateProduct:
    """Atualiza os campos de um produto já existente (nome, categoria, preço,
    descrição, imagens). Não mexe nas variantes — para isso, use
    AddProductVariant. Uso administrativo (RBAC STAFF/ADMIN aplicado no
    api-gateway).

    Todos os campos são opcionais: só o que for passado (não-None) é
    alterado. `clear_original_price=True` remove um preço original existente
    (não dá pra distinguir "não mudar" de "remover" só com None nesse campo).
    """

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        sku: str,
        *,
        name: str | None = None,
        category_slug: str | None = None,
        price: Money | None = None,
        description: str | None = None,
        images: list[str] | None = None,
        original_price: Money | None = None,
        clear_original_price: bool = False,
    ) -> Product:
        product = await self._repository.get_product(sku)
        if product is None:
            raise ProductNotFound(sku)

        category = product.category
        if category_slug is not None and category_slug != product.category.slug:
            found_category = await self._repository.get_category(category_slug)
            if found_category is None:
                raise CategoryNotFound(category_slug)
            category = found_category

        updated = Product(
            sku=product.sku,
            name=name if name is not None else product.name,
            category=category,
            price=price if price is not None else product.price,
            variants=product.variants,
            images=images if images is not None else product.images,
            description=description if description is not None else product.description,
            original_price=(
                None
                if clear_original_price
                else (original_price if original_price is not None else product.original_price)
            ),
        )
        await self._repository.save_product(updated)
        return updated


class AddProductVariant:
    """Adiciona uma variante nova a um produto já existente — uso
    administrativo (RBAC STAFF/ADMIN aplicado no api-gateway). Não permite
    editar/remover uma variante existente (fica para quando precisar de
    verdade); só adicionar."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, variant: ProductVariant) -> Product:
        product = await self._repository.get_product(sku)
        if product is None:
            raise ProductNotFound(sku)

        # SKU de variante é único globalmente (mesma chave usada pelo
        # core-inventory), não só dentro deste produto — daí checar contra
        # o catálogo inteiro, não só `product.variants`.
        if await self._repository.find_variant_owner(variant.sku) is not None:
            raise DuplicateVariantSku(variant.sku)

        updated = Product(
            sku=product.sku,
            name=product.name,
            category=product.category,
            price=product.price,
            variants=[*product.variants, variant],
            images=product.images,
            description=product.description,
            original_price=product.original_price,
        )
        await self._repository.save_product(updated)
        return updated
