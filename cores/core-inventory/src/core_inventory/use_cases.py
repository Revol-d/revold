"""Casos de uso do core-inventory. Orquestram a porta InventoryRepository."""
from __future__ import annotations

from core_inventory.domain import StockLevel, StockLevelNotFound
from core_inventory.ports import InventoryRepository


class GetStockLevel:
    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str) -> StockLevel:
        stock = await self._repository.get(sku)
        if stock is None:
            raise StockLevelNotFound(sku)
        return stock


class CheckAvailability:
    """Usado pelo api-gateway antes de confirmar um AddItem no core-cart —
    os dois cores não se importam entre si (ADR-0002), então essa checagem
    é orquestrada de fora, não dentro de nenhum dos dois cores."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, quantity: int) -> bool:
        stock = await self._repository.get(sku)
        if stock is None:
            return False
        return stock.quantity_available >= quantity


class ReserveStock:
    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, quantity: int) -> StockLevel:
        stock = await self._repository.get(sku)
        if stock is None:
            raise StockLevelNotFound(sku)
        stock.reserve(quantity)
        await self._repository.save(stock)
        return stock


class ReleaseStock:
    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, quantity: int) -> StockLevel:
        stock = await self._repository.get(sku)
        if stock is None:
            raise StockLevelNotFound(sku)
        stock.release(quantity)
        await self._repository.save(stock)
        return stock


class ReceiveStock:
    """Entrada/reposição de estoque — uso administrativo (papel STAFF/ADMIN
    de core_identity.domain.Role, aplicado pelo api-gateway)."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, quantity: int) -> StockLevel:
        stock = await self._repository.get(sku)
        if stock is None:
            stock = StockLevel(sku=sku)
        stock.receive(quantity)
        await self._repository.save(stock)
        return stock


class FulfillReservedStock:
    """Baixa definitiva após confirmação manual da venda (ADR-0005)."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    async def execute(self, sku: str, quantity: int) -> StockLevel:
        stock = await self._repository.get(sku)
        if stock is None:
            raise StockLevelNotFound(sku)
        stock.fulfill(quantity)
        await self._repository.save(stock)
        return stock
