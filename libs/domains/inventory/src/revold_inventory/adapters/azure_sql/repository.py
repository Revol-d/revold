"""Implementação Azure SQL da porta revold_inventory.ports.InventoryRepository.
Espelha adapters/postgres/repository.py -- mesma lógica, só troca de onde o modelo vem."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_inventory.adapters.azure_sql.models import StockLevelModel
from revold_inventory.domain import StockLevel


def _to_domain(model: StockLevelModel) -> StockLevel:
    return StockLevel(
        sku=model.sku,
        quantity_on_hand=model.quantity_on_hand,
        quantity_reserved=model.quantity_reserved,
    )


class AzureSqlInventoryRepository:
    """Implementa revold_inventory.ports.InventoryRepository via SQLAlchemy async
    contra o Azure SQL Database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, sku: str) -> StockLevel | None:
        model = await self._session.get(StockLevelModel, sku)
        return _to_domain(model) if model is not None else None

    async def save(self, stock_level: StockLevel) -> None:
        model = await self._session.get(StockLevelModel, stock_level.sku)
        if model is None:
            model = StockLevelModel(sku=stock_level.sku)
            self._session.add(model)
        model.quantity_on_hand = stock_level.quantity_on_hand
        model.quantity_reserved = stock_level.quantity_reserved
        await self._session.commit()
