"""Implementação Postgres da porta core_inventory.ports.InventoryRepository.

Note que este módulo importa core_inventory (a porta que implementa) mas
core_inventory nunca importa este módulo — a dependência aponta numa via só,
de fora para dentro (Clean/Hexagonal, ver ADR-0002).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from adapters_persistence.inventory.models import StockLevelModel
from core_inventory.domain import StockLevel


def _to_domain(model: StockLevelModel) -> StockLevel:
    return StockLevel(
        sku=model.sku,
        quantity_on_hand=model.quantity_on_hand,
        quantity_reserved=model.quantity_reserved,
    )


class PostgresInventoryRepository:
    """Implementa core_inventory.ports.InventoryRepository via SQLAlchemy async.

    Ao contrário de PostgresProductRepository (só leitura), este adapter
    escreve — por isso commita a própria transação em `save`, em vez de
    depender de quem chamou fazer o commit.
    """

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
