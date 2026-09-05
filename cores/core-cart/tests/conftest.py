from __future__ import annotations

import pytest

from core_cart.domain import Cart


class FakeCartRepository:
    """Adapter fake em memória, mesma forma da porta CartRepository, só para teste."""

    def __init__(self) -> None:
        self._carts: dict[str, Cart] = {}

    async def get(self, cart_id: str) -> Cart | None:
        return self._carts.get(cart_id)

    async def save(self, cart: Cart) -> None:
        self._carts[cart.cart_id] = cart

    async def delete(self, cart_id: str) -> None:
        self._carts.pop(cart_id, None)


@pytest.fixture
def fake_repository() -> FakeCartRepository:
    return FakeCartRepository()
