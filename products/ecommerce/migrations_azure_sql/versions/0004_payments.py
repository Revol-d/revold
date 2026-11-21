"""payments -- quarta tabela migrada para o Azure SQL (ver o plano de migração
Postgres -> Azure SQL, docs internos). Espelha a tabela de
products/ecommerce/migrations/versions/0008_payment_charges.py (Postgres).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_charges",
        sa.Column("charge_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_charge_id", sa.String(length=120), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("amount_currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("pix_qr_code", sa.String(length=4000), nullable=True),
        sa.Column("pix_copy_paste", sa.String(length=2000), nullable=True),
        sa.Column("checkout_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("charge_id"),
    )
    op.create_index("ix_payment_charges_order_id", "payment_charges", ["order_id"], unique=False)
    op.create_index(
        "ix_payment_charges_provider_charge_id",
        "payment_charges",
        ["provider_charge_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_charges_provider_charge_id", table_name="payment_charges")
    op.drop_index("ix_payment_charges_order_id", table_name="payment_charges")
    op.drop_table("payment_charges")
