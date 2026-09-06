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
        self,
        *,
        category_slug: str | None,
        page: int,
        page_size: int,
        search_query: str | None = None,
        sort: str = "relevance",
        sizes: list[str] | None = None,
        colors: list[str] | None = None,
    ) -> tuple[list[Product], int]:
        query = select(ProductModel).options(
            selectinload(ProductModel.category), selectinload(ProductModel.variants)
        )
        count_query = select(func.count()).select_from(ProductModel)
        if category_slug is not None:
            query = query.where(ProductModel.category_slug == category_slug)
            count_query = count_query.where(ProductModel.category_slug == category_slug)
        text_search_rank = None
        if search_query:
            # Full-text search (tsvector, ADR-0014) em vez de ILIKE: tolera
            # acento (config pt_unaccent) e variação de plural/gênero
            # (stemming em português) — "camisêta"/"camisetas" casam com
            # "camiseta" do mesmo jeito. A coluna search_vector é gerada
            # pelo Postgres (migration 0004), nunca escrita pela aplicação.
            ts_query = func.plainto_tsquery("pt_unaccent", search_query)
            match = ProductModel.search_vector.op("@@")(ts_query)
            query = query.where(match)
            count_query = count_query.where(match)
            text_search_rank = func.ts_rank(ProductModel.search_vector, ts_query)
        if sizes or colors:
            # EXISTS em vez de JOIN: uma variante que casa tamanho E cor não
            # deve duplicar a linha do produto no resultado. sizes/colors
            # juntos exigem a MESMA variante casar os dois.
            variant_conditions = [ProductVariantModel.product_sku == ProductModel.sku]
            if sizes:
                variant_conditions.append(ProductVariantModel.size.in_(sizes))
            if colors:
                variant_conditions.append(ProductVariantModel.color.in_(colors))
            variant_match = select(ProductVariantModel.sku).where(*variant_conditions).exists()
            query = query.where(variant_match)
            count_query = count_query.where(variant_match)

        if sort == "price_asc":
            query = query.order_by(ProductModel.price_amount.asc())
        elif sort == "price_desc":
            query = query.order_by(ProductModel.price_amount.desc())
        elif text_search_rank is not None:
            # "relevance" com busca de texto: ordena pelo quão bem o
            # produto casa com a query (ts_rank), não por SKU.
            query = query.order_by(text_search_rank.desc())
        else:
            query = query.order_by(ProductModel.sku.asc())

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

    async def delete_product(self, sku: str) -> None:
        model = await self._session.get(ProductModel, sku)
        if model is None:
            return
        # Carrega as variantes antes de deletar para o cascade
        # "delete-orphan" do relationship funcionar (SQLAlchemy cascateia em
        # Python, não via ON DELETE do banco) — ver ProductModel.variants.
        await self._session.refresh(model, attribute_names=["variants"])
        await self._session.delete(model)
        await self._session.commit()

    async def delete_category(self, slug: str) -> None:
        model = await self._session.get(CategoryModel, slug)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.commit()
