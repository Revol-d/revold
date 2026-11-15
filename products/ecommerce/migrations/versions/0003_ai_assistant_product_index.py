"""ai-assistant product index (pgvector)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mesma dimensão do text-embedding-3-small (Azure OpenAI) — ver ADR-0011.
EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    # A imagem pgvector/pgvector:pg16 (docker-compose.yml) já traz a
    # extensão instalada; só falta habilitá-la neste banco.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "ai_assistant_product_index",
        sa.Column("sku", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_assistant_product_index")
