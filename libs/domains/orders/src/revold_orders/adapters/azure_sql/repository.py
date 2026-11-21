"""Implementação Azure SQL da porta revold_orders.ports.OrderRepository.
Espelha adapters/postgres/repository.py -- mesma lógica, só troca de onde o modelo vem."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from revold_orders.adapters.azure_sql.models import OrderLineModel, OrderModel
from revold_orders.domain import FulfillmentStatus, Money, Order, OrderLine, PaymentStatus


def _to_domain(model: OrderModel) -> Order:
    return Order(
        order_id=model.order_id,
        cart_id=model.cart_id,
        lines=tuple(
            OrderLine(
                sku=line.sku,
                product_name=line.product_name,
                variant_label=line.variant_label,
                unit_price=Money(line.unit_price_amount, line.unit_price_currency),
                quantity=line.quantity,
            )
            for line in model.lines
        ),
        currency=model.currency,
        payment_status=PaymentStatus(model.payment_status),
        fulfillment_status=FulfillmentStatus(model.fulfillment_status),
        created_at=model.created_at,
    )


class AzureSqlOrderRepository:
    """Implementa revold_orders.ports.OrderRepository via SQLAlchemy async contra o
    Azure SQL Database. Mesma restrição do adapter Postgres: as linhas só são
    gravadas na criação do pedido."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, order_id: str) -> Order | None:
        query = (
            select(OrderModel)
            .options(selectinload(OrderModel.lines))
            .where(OrderModel.order_id == order_id)
        )
        model = (await self._session.execute(query)).scalar_one_or_none()
        if model is None:
            return None
        return _to_domain(model)

    async def save(self, order: Order) -> None:
        model = await self._session.get(OrderModel, order.order_id)
        if model is None:
            model = OrderModel(
                order_id=order.order_id,
                cart_id=order.cart_id,
                currency=order.currency,
                created_at=order.created_at,
                lines=[
                    OrderLineModel(
                        line_number=index,
                        sku=line.sku,
                        product_name=line.product_name,
                        variant_label=line.variant_label,
                        unit_price_amount=line.unit_price.amount,
                        unit_price_currency=line.unit_price.currency,
                        quantity=line.quantity,
                    )
                    for index, line in enumerate(order.lines)
                ],
            )
            self._session.add(model)
        model.payment_status = order.payment_status.value
        model.fulfillment_status = order.fulfillment_status.value
        await self._session.commit()

    async def list(
        self,
        *,
        payment_status: PaymentStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Order], int]:
        query = select(OrderModel).options(selectinload(OrderModel.lines))
        count_query = select(func.count()).select_from(OrderModel)
        if payment_status is not None:
            query = query.where(OrderModel.payment_status == payment_status.value)
            count_query = count_query.where(OrderModel.payment_status == payment_status.value)

        total = (await self._session.execute(count_query)).scalar_one()
        query = (
            query.order_by(OrderModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        models = (await self._session.execute(query)).scalars().all()
        return [_to_domain(model) for model in models], total
