from __future__ import annotations

import pytest

from revold_inventory.domain import StockLevel


class FakeInventoryRepository:
    """Adapter fake em memória, mesma forma da porta InventoryRepository, só para teste."""

    def __init__(self) -> None:
        self._levels: dict[str, StockLevel] = {}

    async def get(self, sku: str) -> StockLevel | None:
        return self._levels.get(sku)

    async def save(self, stock_level: StockLevel) -> None:
        self._levels[stock_level.sku] = stock_level


@pytest.fixture
def fake_repository() -> FakeInventoryRepository:
    return FakeInventoryRepository()
