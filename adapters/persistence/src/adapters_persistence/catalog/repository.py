"""Implementação Postgres da porta core_catalog.ports.ProductRepository.

Note que este módulo importa core_catalog (a porta que implementa) mas
core_catalog nunca importa este módulo — a dependência aponta numa via só,
de fora para dentro (Clean/Hexagonal, ver ADR-0002).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters_persistence.catalog.models import CategoryModel, ProductModel
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
