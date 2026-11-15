"""Casos de uso do `orders` (ADR-0023)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from revold_orders.domain import Order, OrderLine, OrderNotFound, PaymentStatus
from revold_orders.ports import OrderRepository


class CreateOrder:
    """Cria um pedido a partir do resumo do carrinho no momento do checkout
    (orquestrado pelo api-gateway — `cart` e `orders` não se importam
    entre si, ver ADR-0002). order_id é gerado aqui, não pelo chamador, para
    que a geração fique num só lugar."""

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(self, *, cart_id: str, lines: list[OrderLine], currency: str = "BRL") -> Order:
        order = Order(
            order_id=uuid.uuid4().hex,
            cart_id=cart_id,
            lines=tuple(lines),
            currency=currency,
            created_at=datetime.now(UTC).isoformat(),
        )
        await self._repository.save(order)
        return order


class GetOrder:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(self, order_id: str) -> Order:
        order = await self._repository.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order


class ListOrders:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(
        self, *, payment_status: PaymentStatus | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[Order], int]:
        return await self._repository.list(
            payment_status=payment_status, page=page, page_size=page_size
        )


class MarkOrderPaid:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(self, order_id: str) -> Order:
        order = await GetOrder(self._repository).execute(order_id)
        order.mark_paid()
        await self._repository.save(order)
        return order


class CancelOrder:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(self, order_id: str) -> Order:
        order = await GetOrder(self._repository).execute(order_id)
        order.cancel()
        await self._repository.save(order)
        return order


class MarkOrderShipped:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(self, order_id: str) -> Order:
        order = await GetOrder(self._repository).execute(order_id)
        order.mark_shipped()
        await self._repository.save(order)
        return order


class MarkOrderDelivered:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def execute(self, order_id: str) -> Order:
        order = await GetOrder(self._repository).execute(order_id)
        order.mark_delivered()
        await self._repository.save(order)
        return order
