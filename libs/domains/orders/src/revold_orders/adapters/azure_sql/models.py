"""Modelos SQLAlchemy de pedidos no Azure SQL. Vivem só no adapter -- revold_orders
não os conhece.

`product_name`/`variant_label` usam `Unicode` (`NVARCHAR`), não `String` (`VARCHAR`) -- são texto
livre copiado do catálogo no momento do pedido (nome do produto, "Azul / M" etc.),
sujeito ao achado de revisão do store-settings (`VARCHAR` com a colação padrão do
servidor troca caractere fora do CP1252 por `?` ao gravar, sem erro; ver
adapters/azure_sql/models.py do store-settings). As demais colunas (`order_id`,
`cart_id`, `currency`, `sku`, status, datas ISO) são códigos/identificadores ASCII
por contrato, continuam `String`.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revold_azure_sql.db import Base


class OrderModel(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_payment_status", "payment_status"),
        Index("ix_orders_created_at", "created_at"),
    )

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cart_id: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    fulfillment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)

    lines: Mapped[list["OrderLineModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderLineModel.line_number",
    )


class OrderLineModel(Base):
    __tablename__ = "order_lines"
    __table_args__ = (Index("ix_order_lines_order_id", "order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    variant_label: Mapped[str] = mapped_column(Unicode(60), nullable=False)
    unit_price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[OrderModel] = relationship(back_populates="lines")
