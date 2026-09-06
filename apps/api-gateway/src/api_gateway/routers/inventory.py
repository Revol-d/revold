"""Router HTTP do core-inventory. Fino: só traduz HTTP <-> caso de uso."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api_gateway.dependencies import (
    get_event_publisher,
    get_inventory_repository,
    get_low_stock_threshold,
    get_metrics_publisher,
)
from api_gateway.orchestration import notify_if_low_stock
from api_gateway.security import require_any_role
from core_events.ports import EventPublisher
from core_identity.domain import AuthenticatedUser, Role
from core_inventory.domain import InsufficientStock, StockLevel, StockLevelNotFound
from core_inventory.ports import InventoryRepository
from core_observability.ports import MetricsPublisher
from core_inventory.schemas import (
    ReceiveStockRequestSchema,
    ReleaseStockRequestSchema,
    ReserveStockRequestSchema,
    StockLevelSchema,
)
from core_inventory.use_cases import (
    GetStockLevel,
    ReceiveStock,
    ReleaseStock,
    ReserveStock,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _stock_to_schema(stock: StockLevel) -> StockLevelSchema:
    return StockLevelSchema(
        sku=stock.sku,
        quantity_on_hand=stock.quantity_on_hand,
        quantity_reserved=stock.quantity_reserved,
        quantity_available=stock.quantity_available,
    )


@router.get("/{sku}", response_model=StockLevelSchema)
async def get_stock_level(
    sku: str, repository: InventoryRepository = Depends(get_inventory_repository)
) -> StockLevelSchema:
    try:
        stock = await GetStockLevel(repository).execute(sku)
    except StockLevelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _stock_to_schema(stock)


@router.post("/{sku}/reserve", response_model=StockLevelSchema)
async def reserve_stock(
    sku: str,
    body: ReserveStockRequestSchema,
    repository: InventoryRepository = Depends(get_inventory_repository),
    event_publisher: EventPublisher = Depends(get_event_publisher),
    low_stock_threshold: int = Depends(get_low_stock_threshold),
    metrics: MetricsPublisher = Depends(get_metrics_publisher),
    _staff: AuthenticatedUser = Depends(require_any_role(Role.STAFF, Role.ADMIN)),
) -> StockLevelSchema:
    # RBAC (ADR-0010): endpoint administrativo — o fluxo de checkout do
    # cliente reserva estoque chamando ReserveStock diretamente (ver
    # api_gateway.routers.cart), não por este endpoint HTTP.
    try:
        stock = await ReserveStock(repository).execute(sku, body.quantity)
    except StockLevelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStock as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await notify_if_low_stock(stock, event_publisher, low_stock_threshold, metrics)
    return _stock_to_schema(stock)


@router.post("/{sku}/release", response_model=StockLevelSchema)
async def release_stock(
    sku: str,
    body: ReleaseStockRequestSchema,
    repository: InventoryRepository = Depends(get_inventory_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(Role.STAFF, Role.ADMIN)),
) -> StockLevelSchema:
    # RBAC (ADR-0010): endpoint administrativo — a compensação de reserva
    # no saga de checkout chama ReleaseStock diretamente (ver
    # api_gateway.routers.cart), não por este endpoint HTTP.
    try:
        stock = await ReleaseStock(repository).execute(sku, body.quantity)
    except StockLevelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _stock_to_schema(stock)


@router.post("/{sku}/receive", response_model=StockLevelSchema)
async def receive_stock(
    sku: str,
    body: ReceiveStockRequestSchema,
    repository: InventoryRepository = Depends(get_inventory_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(Role.STAFF, Role.ADMIN)),
) -> StockLevelSchema:
    # Reposição de estoque: uso administrativo (papel STAFF/ADMIN via
    # RBAC, ver ADR-0010 e api_gateway.security.require_any_role).
    stock = await ReceiveStock(repository).execute(sku, body.quantity)
    return _stock_to_schema(stock)
