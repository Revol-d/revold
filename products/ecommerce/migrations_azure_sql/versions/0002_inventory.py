"""inventory -- segunda tabela migrada para o Azure SQL (ver o plano de migração
Postgres -> Azure SQL, docs internos). Espelha a tabela de
products/ecommerce/migrations/versions/0002_initial_inventory.py (Postgres).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventory_stock_levels",
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("quantity_on_hand", sa.Integer(), nullable=False),
        sa.Column("quantity_reserved", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sku"),
    )


def downgrade() -> None:
    op.drop_table("inventory_stock_levels")
