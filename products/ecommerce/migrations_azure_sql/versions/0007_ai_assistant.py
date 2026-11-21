"""ai_assistant -- sétima tabela migrada para o Azure SQL (ver o plano de
migração Postgres -> Azure SQL, docs internos). Espelha a tabela de
products/ecommerce/migrations/versions/0003_ai_assistant_product_index.py
(Postgres, pgvector), trocando `Vector` (pgvector) pelo tipo customizado em
revold_ai_assistant.adapters.azure_sql.vector_type (SQLAlchemy ainda não tem
suporte nativo ao VECTOR do Azure SQL).

`CREATE VECTOR INDEX` (DiskANN) tem a MESMA restrição do `CREATE FULLTEXT
CATALOG` da migração 0006 -- testado e confirmado: "cannot be used inside a
user transaction" -- por isso também usa `autocommit_block()`.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from revold_ai_assistant.adapters.azure_sql.vector_type import Vector

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_assistant_product_index",
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.PrimaryKeyConstraint("sku"),
    )
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE VECTOR INDEX ix_ai_assistant_product_index_embedding "
            "ON ai_assistant_product_index(embedding) "
            "WITH (metric = 'cosine', type = 'diskann')"
        )


def downgrade() -> None:
    op.drop_table("ai_assistant_product_index")
