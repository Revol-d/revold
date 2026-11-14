"""Pedidos (ADR-0023)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("order_id", sa.String(32), primary_key=True),
        sa.Column("cart_id", sa.String(200), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("fulfillment_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_orders_payment_status", "orders", ["payment_status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.String(32), sa.ForeignKey("orders.order_id"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("variant_label", sa.String(60), nullable=False),
        sa.Column("unit_price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price_currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_payment_status", table_name="orders")
    op.drop_table("orders")
