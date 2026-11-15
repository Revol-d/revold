from __future__ import annotations

import pytest

from revold_orders.domain import Order, PaymentStatus


class FakeOrderRepository:
    """Adapter fake em memória, mesma forma da porta OrderRepository, só
    para teste."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    async def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    async def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    async def list(
        self, *, payment_status: PaymentStatus | None, page: int, page_size: int
    ) -> tuple[list[Order], int]:
        matching = [
            o
            for o in self._orders.values()
            if payment_status is None or o.payment_status == payment_status
        ]
        matching.sort(key=lambda o: o.created_at, reverse=True)
        start = (page - 1) * page_size
        return matching[start : start + page_size], len(matching)


@pytest.fixture
def fake_repository() -> FakeOrderRepository:
    return FakeOrderRepository()
