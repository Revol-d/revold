"""Casos de uso do `cart`."""
from __future__ import annotations

from decimal import Decimal

from revold_cart.domain import Cart, EmptyCart, Money
from revold_cart.ports import CartRepository


class GetOrCreateCart:
    def __init__(self, repository: CartRepository) -> None:
        self._repository = repository

    async def execute(self, cart_id: str) -> Cart:
        cart = await self._repository.get(cart_id)
        if cart is None:
            cart = Cart(cart_id=cart_id)
            await self._repository.save(cart)
        return cart


class AddItem:
    def __init__(self, repository: CartRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        cart_id: str,
        *,
        sku: str,
        name: str,
        variant_label: str,
        unit_price_amount: str,
        currency: str = "BRL",
        quantity: int = 1,
    ) -> Cart:
        cart = await GetOrCreateCart(self._repository).execute(cart_id)
        cart.add_item(
            sku=sku,
            name=name,
            variant_label=variant_label,
            unit_price=Money(Decimal(unit_price_amount), currency),
            quantity=quantity,
        )
        await self._repository.save(cart)
        return cart


class UpdateItemQuantity:
    def __init__(self, repository: CartRepository) -> None:
        self._repository = repository

    async def execute(self, cart_id: str, sku: str, quantity: int) -> Cart:
        cart = await GetOrCreateCart(self._repository).execute(cart_id)
        cart.update_item_quantity(sku, quantity)
        await self._repository.save(cart)
        return cart


class RemoveItem:
    def __init__(self, repository: CartRepository) -> None:
        self._repository = repository

    async def execute(self, cart_id: str, sku: str) -> Cart:
        cart = await GetOrCreateCart(self._repository).execute(cart_id)
        cart.remove_item(sku)
        await self._repository.save(cart)
        return cart


class ClearCart:
    def __init__(self, repository: CartRepository) -> None:
        self._repository = repository

    async def execute(self, cart_id: str) -> None:
        await self._repository.delete(cart_id)


class GetCartForCheckout:
    """Usado pelo api-gateway para montar o CheckoutHandoff (revold_communication).
    Levanta EmptyCart em vez de deixar o orchestrator montar um handoff vazio."""

    def __init__(self, repository: CartRepository) -> None:
        self._repository = repository

    async def execute(self, cart_id: str) -> Cart:
        cart = await self._repository.get(cart_id)
        if cart is None or not cart.items:
            raise EmptyCart(f"Carrinho '{cart_id}' está vazio")
        return cart
