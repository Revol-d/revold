"""Implementação Redis da porta core_cart.ports.CartRepository.

Carrinho é serializado como JSON com TTL (expira sozinho se abandonado —
não precisa de job de limpeza). Chave: "cart:{cart_id}".
"""
from __future__ import annotations

import json
from decimal import Decimal

from redis.asyncio import Redis

from core_cart.domain import Cart, CartItem, Money

_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 dias — carrinho abandonado expira sozinho


def _cart_to_json(cart: Cart) -> str:
    return json.dumps(
        {
            "cart_id": cart.cart_id,
            "currency": cart.currency,
            "items": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "variant_label": item.variant_label,
                    "unit_price_amount": str(item.unit_price.amount),
                    "quantity": item.quantity,
                }
                for item in cart.items
            ],
        }
    )


def _cart_from_json(raw: str) -> Cart:
    data = json.loads(raw)
    cart = Cart(cart_id=data["cart_id"], currency=data.get("currency", "BRL"))
    for item in data["items"]:
        cart.items.append(
            CartItem(
                sku=item["sku"],
                name=item["name"],
                variant_label=item["variant_label"],
                unit_price=Money(Decimal(item["unit_price_amount"]), data.get("currency", "BRL")),
                quantity=item["quantity"],
            )
        )
    return cart


class RedisCartRepository:
    """Implementa core_cart.ports.CartRepository."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, cart_id: str) -> str:
        return f"cart:{cart_id}"

    async def get(self, cart_id: str) -> Cart | None:
        raw = await self._redis.get(self._key(cart_id))
        if raw is None:
            return None
        return _cart_from_json(raw)

    async def save(self, cart: Cart) -> None:
        await self._redis.set(self._key(cart.cart_id), _cart_to_json(cart), ex=_TTL_SECONDS)

    async def delete(self, cart_id: str) -> None:
        await self._redis.delete(self._key(cart_id))
