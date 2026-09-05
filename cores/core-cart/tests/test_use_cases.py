from __future__ import annotations

import pytest

from core_cart.domain import CartItemNotFound, EmptyCart
from core_cart.use_cases import (
    AddItem,
    ClearCart,
    GetCartForCheckout,
    GetOrCreateCart,
    RemoveItem,
    UpdateItemQuantity,
)


async def test_get_or_create_cart_cria_carrinho_vazio(fake_repository):
    cart = await GetOrCreateCart(fake_repository).execute("c1")
    assert cart.cart_id == "c1"
    assert cart.items == []


async def test_add_item_persiste(fake_repository):
    cart = await AddItem(fake_repository).execute(
        "c1", sku="A", name="Camiseta", variant_label="M", unit_price_amount="79.90", quantity=2
    )
    assert cart.items[0].quantity == 2
    reloaded = await GetOrCreateCart(fake_repository).execute("c1")
    assert reloaded.items[0].sku == "A"


async def test_update_item_quantity(fake_repository):
    await AddItem(fake_repository).execute(
        "c1", sku="A", name="Camiseta", variant_label="M", unit_price_amount="79.90"
    )
    cart = await UpdateItemQuantity(fake_repository).execute("c1", "A", 5)
    assert cart.items[0].quantity == 5


async def test_remove_item(fake_repository):
    await AddItem(fake_repository).execute(
        "c1", sku="A", name="Camiseta", variant_label="M", unit_price_amount="79.90"
    )
    cart = await RemoveItem(fake_repository).execute("c1", "A")
    assert cart.items == []


async def test_remove_item_inexistente_levanta_erro(fake_repository):
    with pytest.raises(CartItemNotFound):
        await RemoveItem(fake_repository).execute("c1", "NAO-EXISTE")


async def test_clear_cart(fake_repository):
    await AddItem(fake_repository).execute(
        "c1", sku="A", name="Camiseta", variant_label="M", unit_price_amount="79.90"
    )
    await ClearCart(fake_repository).execute("c1")
    cart = await fake_repository.get("c1")
    assert cart is None


async def test_get_cart_for_checkout_vazio_levanta_erro(fake_repository):
    with pytest.raises(EmptyCart):
        await GetCartForCheckout(fake_repository).execute("c1")


async def test_get_cart_for_checkout_com_itens(fake_repository):
    await AddItem(fake_repository).execute(
        "c1", sku="A", name="Camiseta", variant_label="M", unit_price_amount="79.90"
    )
    cart = await GetCartForCheckout(fake_repository).execute("c1")
    assert len(cart.items) == 1
