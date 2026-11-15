"""Portas (interfaces) que `inventory` espera que a infraestrutura implemente.

Qualquer adapter (Postgres, um fake em memória para teste, etc.) implementa
este Protocol. `inventory` nunca importa SQLAlchemy nem nenhum driver de banco.
"""
from __future__ import annotations

from typing import Protocol

from revold_inventory.domain import StockLevel


class InventoryRepository(Protocol):
    async def get(self, sku: str) -> StockLevel | None: ...

    async def save(self, stock_level: StockLevel) -> None: ...
