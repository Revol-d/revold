"""Implementação Azure SQL da porta revold_catalog.ports.ProductRepository.

Espelha adapters/postgres/repository.py no formato geral, mas a busca full-text é
genuinamente diferente -- não é só trocar sintaxe, o SQL Server exige mais peças que
o `plainto_tsquery`/`ts_rank` do Postgres fazem escondido. Tudo abaixo foi testado
contra um Azure SQL Database real antes de escrever (não assumido):

1. `CONTAINSTABLE` filtra E ranqueia por relevância, mas o SQLAlchemy não tem
   suporte nativo a tabela-valued-function do SQL Server -- usa-se
   `func.CONTAINSTABLE(...).table_valued("KEY", "RANK")` e faz-se JOIN nela.
2. O 3º argumento do `CONTAINSTABLE` (a condição de busca) **não aceita parâmetro
   bindado** -- testado e confirmado: pyodbc sempre declara o parâmetro como
   `nvarchar(max)` via `sp_executesql`, e o SQL Server recusa com
   "argument type nvarchar(max) is invalid for argument 3". O termo entra como
   literal SQL embutido na query (daí a sanitização em `_build_search_condition`).
3. Sem `FORMSOF(INFLECTIONAL, "termo")`, o `CONTAINSTABLE` faz casamento exato de
   palavra -- testado e confirmado: buscar "camiseta" sozinho não achava
   "Camisetas" (plural). `FORMSOF(INFLECTIONAL, ...)` é o equivalente ao stemming
   que o `plainto_tsquery` do Postgres aplica sozinho.
4. O termo de busca passa pela MESMA normalização de acento (`TRANSLATE`) que a
   coluna `search_text` usa (ver models.py) -- senão "ocasiao" nunca bate com
   "ocasião" indexado.
"""
from __future__ import annotations

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from revold_catalog.adapters.azure_sql.models import (
    ACCENTED_CHARS,
    PLAIN_CHARS,
    CategoryModel,
    ProductModel,
    ProductVariantModel,
)
from revold_catalog.domain import Category, Money, Product, ProductVariant

_ACCENT_TABLE = str.maketrans(ACCENTED_CHARS, PLAIN_CHARS)


def _normalize_accents(term: str) -> str:
    return term.translate(_ACCENT_TABLE)


def _build_search_condition(term: str) -> str:
    """Monta o literal SQL do 3º argumento do CONTAINSTABLE. Aspas duplas são
    removidas (sem uso legítimo numa busca de produto; evita ambiguidade de escape
    dentro da linguagem do full-text predicate, que não documenta um jeito de
    escapar `"` dentro de uma frase). Aspas simples são dobradas (escape padrão de
    literal de string do T-SQL, para o literal SQL em si)."""
    normalized = _normalize_accents(term)
    sanitized = normalized.replace('"', "")
    escaped = sanitized.replace("'", "''")
    return f'N\'FORMSOF(INFLECTIONAL, "{escaped}")\''


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


class AzureSqlProductRepository:
    """Implementa revold_catalog.ports.ProductRepository via SQLAlchemy async
    contra o Azure SQL Database."""

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

        rank_column = None
        if search_query:
            condition = _build_search_condition(search_query)
            fts = func.CONTAINSTABLE(
                literal_column("catalog_products"),
                literal_column("search_text"),
                literal_column(condition),
            ).table_valued("KEY", "RANK", name="fts")
            query = query.join(fts, ProductModel.sku == fts.c.KEY)
            count_query = count_query.join(fts, ProductModel.sku == fts.c.KEY)
            rank_column = fts.c.RANK

        if sizes or colors:
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
        elif rank_column is not None:
            query = query.order_by(rank_column.desc())
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
        await self._session.refresh(model, attribute_names=["variants"])
        await self._session.delete(model)
        await self._session.commit()

    async def delete_category(self, slug: str) -> None:
        model = await self._session.get(CategoryModel, slug)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.commit()
