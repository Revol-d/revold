from __future__ import annotations

from decimal import Decimal

import pytest

from core_cart.domain import Cart, CartItemNotFound, Money


def test_add_item_novo():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2


def test_add_item_existente_soma_quantidade():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=1)
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 3


def test_total_soma_subtotais():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2)
    cart.add_item(sku="B", name="Calça", variant_label="38", unit_price=Money(Decimal("100")), quantity=1)
    assert cart.total().amount == Decimal("200")


def test_update_item_quantity():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=1)
    cart.update_item_quantity("A", 5)
    assert cart.items[0].quantity == 5


def test_update_item_inexistente_levanta_erro():
    cart = Cart(cart_id="c1")
    with pytest.raises(CartItemNotFound):
        cart.update_item_quantity("NAO-EXISTE", 1)


def test_remove_item():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=1)
    cart.remove_item("A")
    assert cart.items == []


def test_money_nao_soma_moedas_diferentes():
    with pytest.raises(ValueError):
        Money(Decimal("10"), "BRL") + Money(Decimal("10"), "USD")
