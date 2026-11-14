"""Cobranças de pagamento (ADR-0024)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_charges",
        sa.Column("charge_id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_charge_id", sa.String(120), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("amount_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("pix_qr_code", sa.String(4000), nullable=True),
        sa.Column("pix_copy_paste", sa.String(2000), nullable=True),
        sa.Column("checkout_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_payment_charges_order_id", "payment_charges", ["order_id"])
    op.create_index(
        "ix_payment_charges_provider_charge_id", "payment_charges", ["provider_charge_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_payment_charges_provider_charge_id", table_name="payment_charges")
    op.drop_index("ix_payment_charges_order_id", table_name="payment_charges")
    op.drop_table("payment_charges")
