"""Router HTTP do core-catalog. Fino: só traduz HTTP <-> caso de uso."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api_gateway.dependencies import get_product_repository
from core_catalog.domain import Product, ProductNotFound
from core_catalog.ports import ProductRepository
from core_catalog.schemas import (
    CategorySchema,
    MoneySchema,
    ProductPageSchema,
    ProductSchema,
    ProductVariantSchema,
)
from core_catalog.use_cases import GetProduct, ListCategories, ListProducts

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/categories", response_model=list[CategorySchema])
async def list_categories(
    repository: ProductRepository = Depends(get_product_repository),
) -> list[CategorySchema]:
    categories = await ListCategories(repository).execute()
    return [CategorySchema(slug=c.slug, name=c.name) for c in categories]


@router.get("/products", response_model=ProductPageSchema)
async def list_products(
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductPageSchema:
    try:
        result = await ListProducts(repository).execute(
            category_slug=category, page=page, page_size=page_size
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProductPageSchema(
        items=[_product_to_schema(p) for p in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/products/{sku}", response_model=ProductSchema)
async def get_product(
    sku: str, repository: ProductRepository = Depends(get_product_repository)
) -> ProductSchema:
    try:
        product = await GetProduct(repository).execute(sku)
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _product_to_schema(product)


def _product_to_schema(product: Product) -> ProductSchema:
    return ProductSchema(
        sku=product.sku,
        name=product.name,
        description=product.description,
        category=CategorySchema(slug=product.category.slug, name=product.category.name),
        price=MoneySchema(amount=product.price.amount, currency=product.price.currency),
        original_price=(
            MoneySchema(
                amount=product.original_price.amount, currency=product.original_price.currency
            )
            if product.original_price
            else None
        ),
        variants=[
            ProductVariantSchema(sku=v.sku, size=v.size, color=v.color, in_stock=v.in_stock)
            for v in product.variants
        ],
        images=product.images,
    )
