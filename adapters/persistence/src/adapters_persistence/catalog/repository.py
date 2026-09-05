"""Implementação Postgres da porta core_catalog.ports.ProductRepository.

Note que este módulo importa core_catalog (a porta que implementa) mas
core_catalog nunca importa este módulo — a dependência aponta numa via só,
de fora para dentro (Clean/Hexagonal, ver ADR-0002).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters_persistence.catalog.models import CategoryModel, ProductModel, ProductVariantModel
from core_catalog.domain import Category, Money, Product, ProductVariant


def _to_domain(model: ProductModel) -> Product:
    return Product(
        sku=model.sku,
        name=model.name,
        description=model.description,
        category=Category(slug=model.category.slug, name=model.category.name),
        price=Money(model.price_amount, model.price_currency),
        original_price=(
            Money(model.original_price_amount, model.price_currency)
            if model.original_price_amount is not None
            else None
        ),
        variants=[
            ProductVariant(sku=v.sku, size=v.size, color=v.color, in_stock=v.in_stock)
            for v in model.variants
        ],
        images=list(model.images),
    )


class PostgresProductRepository:
    """Implementa core_catalog.ports.ProductRepository via SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_categories(self) -> list[Category]:
        result = await self._session.execute(select(CategoryModel))
        return [Category(slug=c.slug, name=c.name) for c in result.scalars().all()]

    async def get_category(self, slug: str) -> Category | None:
        model = await self._session.get(CategoryModel, slug)
        return Category(slug=model.slug, name=model.name) if model is not None else None

    async def save_category(self, category: Category) -> None:
        model = await self._session.get(CategoryModel, category.slug)
        if model is None:
            model = CategoryModel(slug=category.slug)
            self._session.add(model)
        model.name = category.name
        await self._session.commit()

    async def list_products(
        self, *, category_slug: str | None, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        query = select(ProductModel).options(
            selectinload(ProductModel.category), selectinload(ProductModel.variants)
        )
        count_query = select(func.count()).select_from(ProductModel)
        if category_slug is not None:
            query = query.where(ProductModel.category_slug == category_slug)
            count_query = count_query.where(ProductModel.category_slug == category_slug)

        total = (await self._session.execute(count_query)).scalar_one()
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(query)
        products = [_to_domain(m) for m in result.scalars().all()]
        return products, total

    async def get_product(self, sku: str) -> Product | None:
        query = (
            select(ProductModel)
            .options(selectinload(ProductModel.category), selectinload(ProductModel.variants))
            .where(ProductModel.sku == sku)
        )
        model = (await self._session.execute(query)).scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    async def save_product(self, product: Product) -> None:
        query = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(ProductModel.sku == product.sku)
        )
        model = (await self._session.execute(query)).scalar_one_or_none()
        if model is None:
            model = ProductModel(sku=product.sku)
            self._session.add(model)

        model.name = product.name
        model.description = product.description
        model.category_slug = product.category.slug
        model.price_amount = product.price.amount
        model.price_currency = product.price.currency
        model.original_price_amount = (
            product.original_price.amount if product.original_price is not None else None
        )
        model.images = list(product.images)

        # Reconcilia as variantes por SKU em vez de substituir a coleção
        # inteira por instâncias novas: se um SKU que já existe no banco
        # fosse recriado do zero, o SQLAlchemy geraria um INSERT para ele
        # (é uma instância transiente, sem identidade de sessão) *antes* do
        # DELETE do órfão do mesmo flush — colidindo com a própria primary
        # key. Por isso as variantes que continuam existindo são atualizadas
        # em cima da instância persistente já carregada; só SKUs realmente
        # novos viram instâncias novas, e só os que saíram da lista são
        # removidos (cascade delete-orphan, ver models.py).
        existing_by_sku = {v.sku: v for v in model.variants}
        incoming_skus = {variant.sku for variant in product.variants}

        for sku, existing_variant in existing_by_sku.items():
            if sku not in incoming_skus:
                model.variants.remove(existing_variant)

        for variant in product.variants:
            matching_variant = existing_by_sku.get(variant.sku)
            if matching_variant is not None:
                matching_variant.size = variant.size
                matching_variant.color = variant.color
                matching_variant.in_stock = variant.in_stock
            else:
                model.variants.append(
                    ProductVariantModel(
                        sku=variant.sku,
                        product_sku=product.sku,
                        size=variant.size,
                        color=variant.color,
                        in_stock=variant.in_stock,
                    )
                )
        await self._session.commit()

    async def find_variant_owner(self, variant_sku: str) -> str | None:
        result = await self._session.execute(
            select(ProductVariantModel.product_sku).where(ProductVariantModel.sku == variant_sku)
        )
        return result.scalar_one_or_none()
