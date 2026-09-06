"""Casos de uso do core-catalog. Orquestram a porta ProductRepository."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from core_catalog.domain import (
    Category,
    CategoryHasProducts,
    CategoryNotFound,
    DuplicateSku,
    DuplicateVariantSku,
    Money,
    Product,
    ProductNotFound,
    ProductVariant,
    VariantNotFound,
)
from core_catalog.ports import MediaStorage, ProductRepository

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")

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
        sizes: list[str] | None = None,
        colors: list[str] | None = None,
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
            sizes=sizes or None,
            colors=colors or None,
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


class AddProductImage:
    """Faz upload de uma imagem (MediaStorage, ADR-0015) e acrescenta a URL
    resultante à lista de imagens do produto. Diferente de UpdateProduct
    (que só aceita substituir a lista inteira por URLs já conhecidas, ex.
    coladas à mão) — este caso de uso é o que atende
    POST /api/catalog/products/{sku}/images (upload de arquivo de verdade).
    """

    def __init__(self, repository: ProductRepository, media_storage: MediaStorage) -> None:
        self._repository = repository
        self._media_storage = media_storage

    async def execute(
        self, sku: str, *, content: bytes, content_type: str, filename: str
    ) -> Product:
        product = await self._repository.get_product(sku)
        if product is None:
            raise ProductNotFound(sku)

        safe_filename = _UNSAFE_FILENAME_CHARS.sub("_", filename) or "imagem"
        key = f"products/{sku}/{uuid.uuid4().hex}-{safe_filename}"
        url = await self._media_storage.upload(key=key, content=content, content_type=content_type)

        product.images = [*product.images, url]
        await self._repository.save_product(product)
        return product


class AddProductVariant:
    """Adiciona uma variante nova a um produto já existente — uso
    administrativo (RBAC STAFF/ADMIN aplicado no api-gateway). Para
    editar/remover uma variante já existente, ver UpdateProductVariant e
    RemoveProductVariant."""

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


class UpdateProductVariant:
    """Edita tamanho/cor/disponibilidade de uma variante já existente — uso
    administrativo (RBAC STAFF/ADMIN aplicado no api-gateway).

    O SKU da variante nunca muda aqui de propósito: é a mesma chave usada
    por core-inventory (StockLevel) para rastrear estoque, e deixar
    renomear por esta rota órfã-ria o estoque já registrado. Quem precisa
    trocar o SKU remove a variante antiga e adiciona uma nova.
    """

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        sku: str,
        variant_sku: str,
        *,
        size: str | None = None,
        color: str | None = None,
        in_stock: bool | None = None,
    ) -> Product:
        product = await self._repository.get_product(sku)
        if product is None:
            raise ProductNotFound(sku)

        existing = next((v for v in product.variants if v.sku == variant_sku), None)
        if existing is None:
            raise VariantNotFound(variant_sku)

        updated_variant = ProductVariant(
            sku=existing.sku,
            size=size if size is not None else existing.size,
            color=color if color is not None else existing.color,
            in_stock=in_stock if in_stock is not None else existing.in_stock,
        )
        updated = Product(
            sku=product.sku,
            name=product.name,
            category=product.category,
            price=product.price,
            variants=[updated_variant if v.sku == variant_sku else v for v in product.variants],
            images=product.images,
            description=product.description,
            original_price=product.original_price,
        )
        await self._repository.save_product(updated)
        return updated


class RemoveProductVariant:
    """Remove uma variante de um produto — uso administrativo (RBAC
    STAFF/ADMIN aplicado no api-gateway). Não mexe em core-inventory: um
    StockLevel já registrado para o SKU removido fica órfão (mesma lógica de
    baixo acoplamento entre bounded contexts do resto do projeto, ADR-0002)
    — não é um bug, é a fronteira entre os dois cores."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, variant_sku: str) -> Product:
        product = await self._repository.get_product(sku)
        if product is None:
            raise ProductNotFound(sku)

        if not any(v.sku == variant_sku for v in product.variants):
            raise VariantNotFound(variant_sku)

        updated = Product(
            sku=product.sku,
            name=product.name,
            category=product.category,
            price=product.price,
            variants=[v for v in product.variants if v.sku != variant_sku],
            images=product.images,
            description=product.description,
            original_price=product.original_price,
        )
        await self._repository.save_product(updated)
        return updated


class DeleteProduct:
    """Remove um produto (e suas variantes) do catálogo — uso administrativo
    (RBAC STAFF/ADMIN aplicado no api-gateway).

    Não mexe em core-cart nem core-inventory: um carrinho que já tinha esse
    produto guarda sua própria cópia de nome/preço (CartItem não referencia
    o catálogo), e um StockLevel em core-inventory fica órfão — mesma
    fronteira de baixo acoplamento entre bounded contexts do resto do
    projeto (ADR-0002), não um descuido.
    """

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str) -> None:
        if await self._repository.get_product(sku) is None:
            raise ProductNotFound(sku)
        await self._repository.delete_product(sku)


class DeleteCategory:
    """Remove uma categoria — uso administrativo (RBAC STAFF/ADMIN aplicado
    no api-gateway). Nunca cascade-remove os produtos da categoria: se
    ainda houver algum, levanta CategoryHasProducts em vez de apagar dado
    silenciosamente."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def execute(self, slug: str) -> None:
        if await self._repository.get_category(slug) is None:
            raise CategoryNotFound(slug)

        _items, total = await self._repository.list_products(
            category_slug=slug, page=1, page_size=1
        )
        if total > 0:
            raise CategoryHasProducts(slug, total)

        await self._repository.delete_category(slug)
