from __future__ import annotations

import pytest
from revold_testing.inventory_factories import StockLevelFactory

from revold_inventory.domain import InsufficientStock, StockLevel


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


class TestFabricaDeDados:
    """Os testes acima cobrem a regra com 1 exemplo numérico escolhido à
    mão cada — nenhum confirma que a invariante se sustenta para qualquer
    combinação válida de quantidades, só para as que alguém lembrou de
    escrever (ver ADR-0012 / `revold_testing.inventory_factories`)."""

    def test_invariante_quantity_available_para_50_niveis_de_estoque_aleatorios(self) -> None:
        for _ in range(50):
            stock = StockLevelFactory()
            assert stock.quantity_available == stock.quantity_on_hand - stock.quantity_reserved
            assert stock.quantity_available >= 0
            assert stock.quantity_reserved <= stock.quantity_on_hand

    def test_fabrica_gera_sku_de_variante_no_formato_real(self) -> None:
        # Formato real usado pelo resto do sistema (ex.
        # "SKU-1234-M-PRETO"), não um placeholder tipo "X" que nenhum
        # teste de integração encontraria de verdade.
        stock = StockLevelFactory()
        assert stock.sku.startswith("SKU-")
        partes = stock.sku.split("-")
        assert len(partes) == 4
