"""Router HTTP do core-inventory. Fino: só traduz HTTP <-> caso de uso."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api_gateway.dependencies import get_inventory_repository
from core_inventory.domain import InsufficientStock, StockLevel, StockLevelNotFound
from core_inventory.ports import InventoryRepository
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
) -> StockLevelSchema:
    try:
        stock = await ReserveStock(repository).execute(sku, body.quantity)
    except StockLevelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStock as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _stock_to_schema(stock)


@router.post("/{sku}/release", response_model=StockLevelSchema)
async def release_stock(
    sku: str,
    body: ReleaseStockRequestSchema,
    repository: InventoryRepository = Depends(get_inventory_repository),
) -> StockLevelSchema:
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
) -> StockLevelSchema:
    # Reposição de estoque: uso administrativo (papel STAFF/ADMIN, RBAC via
    # core_identity — aplicado numa camada futura de autorização do
    # api-gateway; ainda não implementado nesta rodada).
    stock = await ReceiveStock(repository).execute(sku, body.quantity)
    return _stock_to_schema(stock)
