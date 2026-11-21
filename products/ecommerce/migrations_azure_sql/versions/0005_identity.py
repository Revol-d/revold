"""identity -- quinta e ultima tabela da Fase 1 migrada para o Azure SQL (ver o plano
de migração Postgres -> Azure SQL, docs internos). Espelha a tabela de
products/ecommerce/migrations/versions/0005_identity_api_keys.py (Postgres).

`DateTime(timezone=True)` mapeia sozinho para DATETIMEOFFSET no dialeto mssql --
confirmado aqui pelo autogenerate contra um SQL Server real, não assumido.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_api_keys",
        sa.Column("key_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key_id"),
        sa.UniqueConstraint("key_hash", name="identity_api_keys_key_hash_key"),
    )
    op.create_index(
        "ix_identity_api_keys_key_hash", "identity_api_keys", ["key_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_identity_api_keys_key_hash", table_name="identity_api_keys")
    op.drop_table("identity_api_keys")
