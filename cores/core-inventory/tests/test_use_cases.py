from __future__ import annotations

import pytest

from core_inventory.domain import InsufficientStock, StockLevel, StockLevelNotFound
from core_inventory.use_cases import (
    CheckAvailability,
    FulfillReservedStock,
    GetStockLevel,
    ReceiveStock,
    ReleaseStock,
    ReserveStock,
)


async def test_get_stock_level_raises_when_missing(fake_repository) -> None:
    with pytest.raises(StockLevelNotFound):
        await GetStockLevel(fake_repository).execute("MISSING")


async def test_get_stock_level_returns_existing(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=5))
    stock = await GetStockLevel(fake_repository).execute("X")
    assert stock.quantity_on_hand == 5


async def test_check_availability_false_when_sku_unknown(fake_repository) -> None:
    assert await CheckAvailability(fake_repository).execute("MISSING", 1) is False


async def test_check_availability_compares_against_available(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=5, quantity_reserved=3))
    assert await CheckAvailability(fake_repository).execute("X", 2) is True
    assert await CheckAvailability(fake_repository).execute("X", 3) is False


async def test_reserve_stock_persists_reservation(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=5))
    stock = await ReserveStock(fake_repository).execute("X", 2)
    assert stock.quantity_reserved == 2
    persisted = await fake_repository.get("X")
    assert persisted is not None
    assert persisted.quantity_reserved == 2


async def test_reserve_stock_raises_when_sku_unknown(fake_repository) -> None:
    with pytest.raises(StockLevelNotFound):
        await ReserveStock(fake_repository).execute("MISSING", 1)


async def test_reserve_stock_raises_insufficient_stock(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=1))
    with pytest.raises(InsufficientStock):
        await ReserveStock(fake_repository).execute("X", 2)


async def test_release_stock_frees_reservation(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=5, quantity_reserved=3))
    stock = await ReleaseStock(fake_repository).execute("X", 1)
    assert stock.quantity_reserved == 2


async def test_receive_stock_creates_level_when_missing(fake_repository) -> None:
    stock = await ReceiveStock(fake_repository).execute("NEW-SKU", 10)
    assert stock.quantity_on_hand == 10
    persisted = await fake_repository.get("NEW-SKU")
    assert persisted is not None
    assert persisted.quantity_on_hand == 10


async def test_receive_stock_adds_to_existing_level(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=5))
    stock = await ReceiveStock(fake_repository).execute("X", 10)
    assert stock.quantity_on_hand == 15


async def test_fulfill_reserved_stock_lowers_on_hand_and_reserved(fake_repository) -> None:
    await fake_repository.save(StockLevel(sku="X", quantity_on_hand=5, quantity_reserved=2))
    stock = await FulfillReservedStock(fake_repository).execute("X", 2)
    assert stock.quantity_on_hand == 3
    assert stock.quantity_reserved == 0


async def test_fulfill_reserved_stock_raises_when_sku_unknown(fake_repository) -> None:
    with pytest.raises(StockLevelNotFound):
        await FulfillReservedStock(fake_repository).execute("MISSING", 1)
