from __future__ import annotations

from decimal import Decimal

import pytest

from core_orders.domain import InvalidOrderTransition, Money, OrderLine, OrderNotFound, PaymentStatus
from core_orders.use_cases import (
    CancelOrder,
    CreateOrder,
    GetOrder,
    ListOrders,
    MarkOrderDelivered,
    MarkOrderPaid,
    MarkOrderShipped,
)


def _line(sku: str = "A") -> OrderLine:
    return OrderLine(
        sku=sku, product_name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2
    )


async def test_create_order_gera_id_e_persiste(fake_repository) -> None:
    order = await CreateOrder(fake_repository).execute(cart_id="c1", lines=[_line()])
    assert order.order_id
    assert order.cart_id == "c1"
    assert order.total() == Money(Decimal("100"))

    persisted = await fake_repository.get(order.order_id)
    assert persisted == order


async def test_get_order_inexistente_levanta_order_not_found(fake_repository) -> None:
    with pytest.raises(OrderNotFound):
        await GetOrder(fake_repository).execute("nao-existe")


async def test_mark_order_paid(fake_repository) -> None:
    order = await CreateOrder(fake_repository).execute(cart_id="c1", lines=[_line()])
    updated = await MarkOrderPaid(fake_repository).execute(order.order_id)
    assert updated.payment_status == PaymentStatus.PAID

    persisted = await fake_repository.get(order.order_id)
    assert persisted is not None
    assert persisted.payment_status == PaymentStatus.PAID


async def test_cancel_order(fake_repository) -> None:
    order = await CreateOrder(fake_repository).execute(cart_id="c1", lines=[_line()])
    updated = await CancelOrder(fake_repository).execute(order.order_id)
    assert updated.payment_status == PaymentStatus.CANCELLED


async def test_mark_shipped_antes_de_pago_propaga_invalid_transition(fake_repository) -> None:
    order = await CreateOrder(fake_repository).execute(cart_id="c1", lines=[_line()])
    with pytest.raises(InvalidOrderTransition):
        await MarkOrderShipped(fake_repository).execute(order.order_id)


async def test_fluxo_completo_pago_enviado_entregue(fake_repository) -> None:
    order = await CreateOrder(fake_repository).execute(cart_id="c1", lines=[_line()])
    await MarkOrderPaid(fake_repository).execute(order.order_id)
    await MarkOrderShipped(fake_repository).execute(order.order_id)
    delivered = await MarkOrderDelivered(fake_repository).execute(order.order_id)
    assert delivered.fulfillment_status.value == "delivered"


async def test_list_orders_filtra_por_payment_status_e_pagina(fake_repository) -> None:
    o1 = await CreateOrder(fake_repository).execute(cart_id="c1", lines=[_line("A")])
    await CreateOrder(fake_repository).execute(cart_id="c2", lines=[_line("B")])
    await MarkOrderPaid(fake_repository).execute(o1.order_id)

    paid, total_paid = await ListOrders(fake_repository).execute(payment_status=PaymentStatus.PAID)
    assert total_paid == 1
    assert paid[0].order_id == o1.order_id

    all_orders, total_all = await ListOrders(fake_repository).execute(page=1, page_size=1)
    assert total_all == 2
    assert len(all_orders) == 1
