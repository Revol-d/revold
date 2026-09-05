from __future__ import annotations

import pytest

from core_inventory.domain import InsufficientStock, StockLevel


def test_quantity_available_is_on_hand_minus_reserved() -> None:
    stock = StockLevel(sku="TSHIRT-M-BLACK", quantity_on_hand=10, quantity_reserved=3)
    assert stock.quantity_available == 7


def test_rejects_negative_quantities() -> None:
    with pytest.raises(ValueError):
        StockLevel(sku="X", quantity_on_hand=-1)
    with pytest.raises(ValueError):
        StockLevel(sku="X", quantity_reserved=-1)


def test_rejects_reserved_greater_than_on_hand() -> None:
    with pytest.raises(ValueError):
        StockLevel(sku="X", quantity_on_hand=1, quantity_reserved=2)


def test_reserve_reduces_availability() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=5)
    stock.reserve(3)
    assert stock.quantity_reserved == 3
    assert stock.quantity_available == 2


def test_reserve_beyond_available_raises_insufficient_stock() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=2)
    with pytest.raises(InsufficientStock) as exc_info:
        stock.reserve(3)
    assert exc_info.value.sku == "X"
    assert exc_info.value.requested == 3
    assert exc_info.value.available == 2


def test_reserve_rejects_non_positive_quantity() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=5)
    with pytest.raises(ValueError):
        stock.reserve(0)


def test_release_returns_reserved_to_available() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=5, quantity_reserved=3)
    stock.release(2)
    assert stock.quantity_reserved == 1
    assert stock.quantity_available == 4


def test_release_beyond_reserved_raises() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=5, quantity_reserved=2)
    with pytest.raises(ValueError):
        stock.release(3)


def test_receive_increases_on_hand() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=5)
    stock.receive(10)
    assert stock.quantity_on_hand == 15
    assert stock.quantity_available == 15


def test_receive_rejects_non_positive_quantity() -> None:
    stock = StockLevel(sku="X")
    with pytest.raises(ValueError):
        stock.receive(0)


def test_fulfill_reduces_on_hand_and_reserved_together() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=10, quantity_reserved=4)
    stock.fulfill(4)
    assert stock.quantity_on_hand == 6
    assert stock.quantity_reserved == 0
    assert stock.quantity_available == 6


def test_fulfill_beyond_reserved_raises() -> None:
    stock = StockLevel(sku="X", quantity_on_hand=10, quantity_reserved=2)
    with pytest.raises(ValueError):
        stock.fulfill(3)
