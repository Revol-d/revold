"""Router HTTP do `catalog`. Fino: só traduz HTTP <-> caso de uso."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from api_gateway.dependencies import get_event_publisher, get_media_storage, get_product_repository
from api_gateway.security import require_any_role
from revold_catalog.domain import (
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
from revold_catalog.ports import MediaStorage, ProductRepository
from revold_catalog.application.schemas import (
    CategorySchema,
    CreateCategoryRequestSchema,
    CreateProductRequestSchema,
    CreateProductVariantSchema,
    MoneySchema,
    ProductPageSchema,
    ProductSchema,
    ProductVariantSchema,
    UpdateProductRequestSchema,
    UpdateProductVariantRequestSchema,
)
from revold_catalog.application.use_cases import (
    AddProductImage,
    AddProductVariant,
    CreateCategory,
    CreateProduct,
    DeleteCategory,
    DeleteProduct,
    GetProduct,
    ListCategories,
    ListProducts,
    RemoveProductVariant,
    UpdateProduct,
    UpdateProductVariant,
)
from revold_platform.events.domain import DomainEvent
from revold_platform.events.ports import EventPublisher
from revold_identity.domain import AuthenticatedUser
from revold_identity.domain import Role as UserRole

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
    q: str | None = Query(default=None),
    sort: str = Query(default="relevance"),
    size: list[str] | None = Query(default=None),
    color: list[str] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductPageSchema:
    try:
        result = await ListProducts(repository).execute(
            category_slug=category,
            search_query=q,
            sort=sort,
            sizes=size,
            colors=color,
            page=page,
            page_size=page_size,
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
    event_publisher: EventPublisher = Depends(get_event_publisher),
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
    await _publish_product_updated(event_publisher, product.sku)
    return _product_to_schema(product)


@router.patch("/products/{sku}", response_model=ProductSchema)
async def update_product(
    sku: str,
    body: UpdateProductRequestSchema,
    repository: ProductRepository = Depends(get_product_repository),
    event_publisher: EventPublisher = Depends(get_event_publisher),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ProductSchema:
    try:
        product = await UpdateProduct(repository).execute(
            sku,
            name=body.name,
            category_slug=body.category_slug,
            price=(
                Money(amount=body.price.amount, currency=body.price.currency)
                if body.price
                else None
            ),
            description=body.description,
            images=body.images,
            original_price=(
                Money(amount=body.original_price.amount, currency=body.original_price.currency)
                if body.original_price
                else None
            ),
            clear_original_price=body.clear_original_price,
        )
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CategoryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _publish_product_updated(event_publisher, product.sku)
    return _product_to_schema(product)


@router.post("/products/{sku}/variants", response_model=ProductSchema, status_code=201)
async def add_product_variant(
    sku: str,
    body: CreateProductVariantSchema,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ProductSchema:
    variant = ProductVariant(sku=body.sku, size=body.size, color=body.color, in_stock=body.in_stock)
    try:
        product = await AddProductVariant(repository).execute(sku, variant)
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateVariantSku as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _product_to_schema(product)


_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB — generoso pra foto de celular, evita abuso de upload
_ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/products/{sku}/images", response_model=ProductSchema, status_code=201)
async def add_product_image(
    sku: str,
    file: UploadFile = File(...),
    repository: ProductRepository = Depends(get_product_repository),
    media_storage: MediaStorage = Depends(get_media_storage),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ProductSchema:
    """Upload de imagem de verdade (ADR-0015) — diferente de PATCH
    /products/{sku}, que só aceita substituir a lista de imagens por URLs já
    conhecidas (coladas à mão)."""
    if file.content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo de arquivo não suportado: {file.content_type!r}. "
            f"Use um de: {sorted(_ALLOWED_IMAGE_CONTENT_TYPES)}",
        )
    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=422, detail=f"Arquivo maior que o limite de {_MAX_IMAGE_BYTES // (1024 * 1024)}MB"
        )
    try:
        product = await AddProductImage(repository, media_storage).execute(
            sku,
            content=content,
            content_type=file.content_type,
            filename=file.filename or "imagem",
        )
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _product_to_schema(product)


@router.patch("/products/{sku}/variants/{variant_sku}", response_model=ProductSchema)
async def update_product_variant(
    sku: str,
    variant_sku: str,
    body: UpdateProductVariantRequestSchema,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ProductSchema:
    try:
        product = await UpdateProductVariant(repository).execute(
            sku, variant_sku, size=body.size, color=body.color, in_stock=body.in_stock
        )
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VariantNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _product_to_schema(product)


@router.delete("/products/{sku}/variants/{variant_sku}", response_model=ProductSchema)
async def remove_product_variant(
    sku: str,
    variant_sku: str,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> ProductSchema:
    try:
        product = await RemoveProductVariant(repository).execute(sku, variant_sku)
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VariantNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _product_to_schema(product)


@router.delete("/products/{sku}", status_code=204)
async def delete_product(
    sku: str,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> Response:
    try:
        await DeleteProduct(repository).execute(sku)
    except ProductNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.delete("/categories/{slug}", status_code=204)
async def delete_category(
    slug: str,
    repository: ProductRepository = Depends(get_product_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(UserRole.STAFF, UserRole.ADMIN)),
) -> Response:
    try:
        await DeleteCategory(repository).execute(slug)
    except CategoryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CategoryHasProducts as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=204)


async def _publish_product_updated(event_publisher: EventPublisher, sku: str) -> None:
    """Publica product.updated depois de criar/editar um produto — o
    índice vetorial de IA (RAG) reindexa só esse SKU de forma assíncrona
    (ver revold_ecommerce.application.event_handlers.handle_product_updated, ADR-0013),
    em vez de ficar desatualizado até alguém clicar em "reindexar tudo" no
    admin."""
    await event_publisher.publish(DomainEvent(name="product.updated", payload={"sku": sku}))


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
