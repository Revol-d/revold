from __future__ import annotations

from decimal import Decimal

import pytest

from revold_orders.domain import (
    FulfillmentStatus,
    InvalidOrderTransition,
    Money,
    Order,
    OrderLine,
    PaymentStatus,
)


def _line(sku: str = "A", quantity: int = 2, price: str = "50") -> OrderLine:
    return OrderLine(
        sku=sku,
        product_name="Camiseta",
        variant_label="M / Azul",
        unit_price=Money(Decimal(price)),
        quantity=quantity,
    )


def _order(**kwargs) -> Order:
    defaults = dict(order_id="o1", cart_id="c1", lines=(_line(),))
    defaults.update(kwargs)
    return Order(**defaults)


def test_money_nao_aceita_valor_negativo() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("-1"))


def test_order_line_nao_aceita_quantidade_menor_que_1() -> None:
    with pytest.raises(ValueError):
        OrderLine(
            sku="A", product_name="Camiseta", variant_label="M", unit_price=Money(Decimal("10")), quantity=0
        )


def test_order_line_subtotal() -> None:
    line = _line(quantity=3, price="10.50")
    assert line.subtotal() == Money(Decimal("31.50"))


def test_order_sem_linha_nenhuma_e_invalido() -> None:
    with pytest.raises(ValueError):
        Order(order_id="o1", cart_id="c1", lines=())


def test_order_total_soma_todas_as_linhas() -> None:
    order = _order(lines=(_line(sku="A", quantity=2, price="50"), _line(sku="B", quantity=1, price="30")))
    assert order.total() == Money(Decimal("130"))


def test_order_nasce_pending_pending() -> None:
    order = _order()
    assert order.payment_status == PaymentStatus.PENDING
    assert order.fulfillment_status == FulfillmentStatus.PENDING


def test_mark_paid_a_partir_de_pending() -> None:
    order = _order()
    order.mark_paid()
    assert order.payment_status == PaymentStatus.PAID


def test_mark_paid_duas_vezes_e_invalido() -> None:
    order = _order()
    order.mark_paid()
    with pytest.raises(InvalidOrderTransition):
        order.mark_paid()


def test_cancel_a_partir_de_pending() -> None:
    order = _order()
    order.cancel()
    assert order.payment_status == PaymentStatus.CANCELLED


def test_cancel_pedido_ja_pago_e_invalido() -> None:
    order = _order()
    order.mark_paid()
    with pytest.raises(InvalidOrderTransition):
        order.cancel()


def test_mark_shipped_exige_pagamento_confirmado() -> None:
    order = _order()
    with pytest.raises(InvalidOrderTransition):
        order.mark_shipped()


def test_mark_shipped_apos_pago() -> None:
    order = _order()
    order.mark_paid()
    order.mark_shipped()
    assert order.fulfillment_status == FulfillmentStatus.SHIPPED


def test_mark_delivered_exige_envio_previo() -> None:
    order = _order()
    order.mark_paid()
    with pytest.raises(InvalidOrderTransition):
        order.mark_delivered()


def test_mark_delivered_apos_shipped() -> None:
    order = _order()
    order.mark_paid()
    order.mark_shipped()
    order.mark_delivered()
    assert order.fulfillment_status == FulfillmentStatus.DELIVERED
