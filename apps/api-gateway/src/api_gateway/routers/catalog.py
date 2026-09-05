"""Router HTTP do core-catalog. Fino: só traduz HTTP <-> caso de uso."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api_gateway.dependencies import get_product_repository
from api_gateway.security import require_any_role
from core_catalog.domain import CategoryNotFound, DuplicateSku, Money, Product, ProductNotFound, ProductVariant
from core_catalog.ports import ProductRepository
from core_catalog.schemas import (
    CategorySchema,
    CreateCategoryRequestSchema,
    CreateProductRequestSchema,
    MoneySchema,
    ProductPageSchema,
    ProductSchema,
    ProductVariantSchema,
)
from core_catalog.use_cases import (
    CreateCategory,
    CreateProduct,
    GetProduct,
    ListCategories,
    ListProducts,
)
from core_identity.domain import AuthenticatedUser
from core_identity.domain import Role as UserRole

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


@router.post("/categories", response_model=CategorySchema, status_code=201)
async def create_category(
    body: CreateCategoryRequestSchema,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> CategorySchema:
    category = await CreateCategory(repository).execute(slug=body.slug, name=body.name)
    return CategorySchema(slug=category.slug, name=category.name)


@router.post("/products", response_model=ProductSchema, status_code=201)
async def create_product(
    body: CreateProductRequestSchema,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ProductSchema:
    try:
        product = await CreateProduct(repository).execute(
            sku=body.sku,
            name=body.name,
            category_slug=body.category_slug,
            price=Money(amount=body.price.amount, currency=body.price.currency),
            description=body.description,
            images=body.images,
            original_price=(
                Money(amount=body.original_price.amount, currency=body.original_price.currency)
                if body.original_price
                else None
            ),
            variants=[
                ProductVariant(sku=v.sku, size=v.size, color=v.color, in_stock=v.in_stock)
                for v in body.variants
            ],
        )
    except CategoryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateSku as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
