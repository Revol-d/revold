"""busca full-text de produtos (tsvector + unaccent) — ADR-0014

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # unaccent: permite achar "camisêta"/"camiseta" com a mesma busca (o
    # ILIKE anterior nunca tolerava isso). pt_unaccent copia a configuração
    # "portuguese" (stemming de plural/gênero/conjugação) e troca o
    # dicionário de palavra pra normalizar acento antes de indexar/buscar.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'pt_unaccent') THEN
                CREATE TEXT SEARCH CONFIGURATION pt_unaccent (COPY = portuguese);
                ALTER TEXT SEARCH CONFIGURATION pt_unaccent
                    ALTER MAPPING FOR hword, hword_part, word
                    WITH unaccent, portuguese_stem;
            END IF;
        END
        $$;
        """
    )
    # Coluna gerada (GENERATED ALWAYS ... STORED): o Postgres recalcula
    # sozinho toda vez que name/description mudam — nenhum código de
    # aplicação (nem trigger) precisa manter isso sincronizado.
    op.add_column(
        "catalog_products",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('pt_unaccent', coalesce(name, '') || ' ' || coalesce(description, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_catalog_products_search_vector",
        "catalog_products",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_products_search_vector", table_name="catalog_products")
    op.drop_column("catalog_products", "search_vector")
