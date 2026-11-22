"""store settings inicial -- primeira tabela migrada para o Azure SQL (ver o
plano de migração Postgres -> Azure SQL, docs internos). Espelha a tabela de
products/ecommerce/migrations/versions/0006_store_settings.py (Postgres).

`store_name`/`store_address` usam `Unicode` (`NVARCHAR`), não `String`
(`VARCHAR`) -- achado de revisão: `VARCHAR` com a colação padrão do servidor
troca caractere fora do CP1252 por `?` ao gravar, sem erro (ver
adapters/azure_sql/models.py).

Revision ID: 0001
Revises:
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_settings",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("cnpj", sa.String(length=30), nullable=False),
        sa.Column("store_name", sa.Unicode(length=200), nullable=False),
        sa.Column("contact_email", sa.String(length=200), nullable=False),
        sa.Column("contact_phone", sa.String(length=30), nullable=False),
        sa.Column("store_address", sa.Unicode(length=500), nullable=False),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("store_settings")
