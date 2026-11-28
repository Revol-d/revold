"""ai_assistant -- sétima tabela migrada para o Azure SQL (ver o plano de
migração Postgres -> Azure SQL, docs internos). Espelha a tabela de
products/ecommerce/migrations/versions/0003_ai_assistant_product_index.py
(Postgres, pgvector), trocando `Vector` (pgvector) pelo tipo customizado em
revold_ai_assistant.adapters.azure_sql.vector_type (SQLAlchemy ainda não tem
suporte nativo ao VECTOR do Azure SQL).

Sem `CREATE VECTOR INDEX` (DiskANN) de propósito -- ver a nota longa em
adapters/azure_sql/models.py: a versão do índice com suporte a DML só está GA
no Azure SQL Database real, e mesmo um SQL Server 2025 em caixa cria a versão
antiga (tabela somente-leitura). `VECTOR_DISTANCE` funciona sem índice (scan
completo); criar o índice fica para uma tarefa operacional futura.

`name`/`description` usam `Unicode`/`UnicodeText` (`NVARCHAR`/`NTEXT`), não
`String`/`Text` (`VARCHAR`/`TEXT`) -- achado de revisão do store-settings (ver
adapters/azure_sql/models.py).

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
        sa.Column("name", sa.Unicode(length=255), nullable=False),
        sa.Column("description", sa.UnicodeText(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.PrimaryKeyConstraint("sku"),
    )


def downgrade() -> None:
    op.drop_table("ai_assistant_product_index")
