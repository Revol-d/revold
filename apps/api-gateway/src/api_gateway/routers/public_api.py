"""API pública/parceiro (ADR-0016) — exposição de dados do catálogo para
integrações externas (ex. um ERP, um segundo canal de venda), separada do
que storefront/admin-dashboard consomem via /api/catalog. Autenticação por
API key (header X-API-Key) + rate limit por chave, nunca por sessão de
cookie (ver api_gateway.security.require_api_key_principal).

Hoje só um endpoint de leitura de produtos, como prova de conceito do leaf
inteiro (API key + rate limiter) — mais endpoints entram aqui conforme
surgir necessidade real de um parceiro."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api_gateway.dependencies import get_product_repository
from api_gateway.security import require_api_key_principal
from core_catalog.domain import Product
from core_catalog.ports import ProductRepository
from core_catalog.schemas import (
    CategorySchema,
    MoneySchema,
    ProductPageSchema,
    ProductSchema,
    ProductVariantSchema,
)
from core_catalog.use_cases import ListProducts
from core_identity.domain import ApiKeyPrincipal

router = APIRouter(prefix="/api/public/v1", tags=["public-api"])


@router.get("/products", response_model=ProductPageSchema)
async def list_products_public(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    repository: ProductRepository = Depends(get_product_repository),
    _principal: ApiKeyPrincipal = Depends(require_api_key_principal),
) -> ProductPageSchema:
    try:
        result = await ListProducts(repository).execute(page=page, page_size=page_size)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ProductPageSchema(
        items=[_product_to_schema(p) for p in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


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
