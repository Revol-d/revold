"""Modelos SQLAlchemy de pedidos. Vivem só no adapter — core_orders não os
conhece (ADR-0002, ADR-0023).

Um pedido é criado uma única vez com todas as suas linhas (ver
core_orders.use_cases.CreateOrder) — depois disso só os campos de status
mudam (payment_status/fulfillment_status), as linhas nunca são reescritas,
por isso `save()` no repository só insere linha quando o pedido é novo.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters_persistence.db import Base


class OrderModel(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cart_id: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    fulfillment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # ISO 8601 (mesma representação que core_orders.domain.Order.created_at)
    # — ordena corretamente como string, sem precisar de um tipo DateTime.
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)

    lines: Mapped[list["OrderLineModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderLineModel.line_number",
    )


class OrderLineModel(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    variant_label: Mapped[str] = mapped_column(String(60), nullable=False)
    unit_price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[OrderModel] = relationship(back_populates="lines")
