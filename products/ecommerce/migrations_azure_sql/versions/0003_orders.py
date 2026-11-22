"""orders -- terceira tabela migrada para o Azure SQL (ver o plano de migração
Postgres -> Azure SQL, docs internos). Espelha as tabelas de
products/ecommerce/migrations/versions/0007_orders.py (Postgres).

`product_name`/`variant_label` usam `Unicode` (`NVARCHAR`), não `String`
(`VARCHAR`) -- mesmo achado de revisão do store-settings (ver
adapters/azure_sql/models.py): são texto livre copiado do catálogo no
momento do pedido, sujeito ao mesmo risco de truncamento silencioso por
colação.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("order_id", sa.String(length=32), nullable=False),
        sa.Column("cart_id", sa.String(length=200), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("payment_status", sa.String(length=20), nullable=False),
        sa.Column("fulfillment_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("order_id"),
    )
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_orders_payment_status", "orders", ["payment_status"], unique=False)
    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.Unicode(length=200), nullable=False),
        sa.Column("variant_label", sa.Unicode(length=60), nullable=False),
        sa.Column("unit_price_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit_price_currency", sa.String(length=3), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_payment_status", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_table("orders")
