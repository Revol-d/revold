"""catalog -- sexta tabela migrada para o Azure SQL (ver o plano de migração
Postgres -> Azure SQL, docs internos). Espelha as tabelas de
products/ecommerce/migrations/versions/0001_initial_catalog.py e
0004_catalog_search_vector.py (Postgres), mas a busca full-text é genuinamente
diferente -- ver a nota longa em adapters/azure_sql/repository.py.

`CREATE FULLTEXT CATALOG`/`CREATE FULLTEXT INDEX` não podem rodar dentro de
transação (testado e confirmado: "cannot be used inside a user transaction") --
por isso o bloco usa `op.get_context().autocommit_block()`, o jeito documentado
do próprio Alembic pra DDL que exige autocommit (CREATE DATABASE, ALTER DATABASE,
e esta).

`name`/`description`/`search_text`/`color` usam `Unicode`/`UnicodeText`
(`NVARCHAR`/`NTEXT`), não `String`/`Text` (`VARCHAR`/`TEXT`) -- achado de revisão
do store-settings (ver adapters/azure_sql/models.py): `VARCHAR`/`TEXT` com a
colação padrão do servidor trocam caractere fora do CP1252 por `?` ao gravar, sem
erro. `search_text` segue o mesmo tipo porque `TRANSLATE` opera sobre `name`/
`description` -- se eles são Unicode, o resultado computado também precisa ser,
senão a corrupção reaparece no armazenamento da própria coluna computada.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_categories",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.Unicode(length=200), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.create_table(
        "catalog_products",
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.Unicode(length=200), nullable=False),
        sa.Column("description", sa.UnicodeText(), nullable=False),
        sa.Column("category_slug", sa.String(length=120), nullable=False),
        sa.Column("price_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("price_currency", sa.String(length=3), nullable=False),
        sa.Column("original_price_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column(
            "search_text",
            sa.UnicodeText(),
            sa.Computed(
                "TRANSLATE(COALESCE(name, N'') + N' ' + COALESCE(description, N''), "
                "N'áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ', "
                "N'aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC')",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["category_slug"], ["catalog_categories.slug"]),
        sa.PrimaryKeyConstraint("sku"),
    )
    op.create_index(
        "ix_catalog_products_category_slug", "catalog_products", ["category_slug"], unique=False
    )
    op.create_table(
        "catalog_product_variants",
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("product_sku", sa.String(length=64), nullable=False),
        sa.Column("size", sa.String(length=20), nullable=False),
        sa.Column("color", sa.Unicode(length=60), nullable=False),
        sa.Column("in_stock", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["product_sku"], ["catalog_products.sku"]),
        sa.PrimaryKeyConstraint("sku"),
    )
    op.create_index(
        "ix_catalog_variants_product_sku", "catalog_product_variants", ["product_sku"], unique=False
    )

    with op.get_context().autocommit_block():
        op.execute(
            "IF NOT EXISTS (SELECT 1 FROM sys.fulltext_catalogs WHERE name = 'catalog_fts') "
            "CREATE FULLTEXT CATALOG catalog_fts AS DEFAULT"
        )
        # KEY INDEX exige o nome literal do índice da PK -- o SQL Server gera esse
        # nome sozinho (ex. PK__catalog_p__...), por isso descobre em sys.indexes
        # em vez de adivinhar, via SQL dinâmico (precisa ser 1 batch só).
        op.execute(
            """
            DECLARE @pk_name sysname;
            SELECT @pk_name = i.name
            FROM sys.indexes i JOIN sys.tables t ON t.object_id = i.object_id
            WHERE t.name = 'catalog_products' AND i.is_primary_key = 1;
            DECLARE @sql nvarchar(max) = N'CREATE FULLTEXT INDEX ON catalog_products'
                + N'(search_text LANGUAGE ''Portuguese'') KEY INDEX [' + @pk_name + N']';
            EXEC sp_executesql @sql;
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP FULLTEXT INDEX ON catalog_products")
        op.execute("DROP FULLTEXT CATALOG catalog_fts")
    op.drop_index("ix_catalog_variants_product_sku", table_name="catalog_product_variants")
    op.drop_table("catalog_product_variants")
    op.drop_index("ix_catalog_products_category_slug", table_name="catalog_products")
    op.drop_table("catalog_products")
    op.drop_table("catalog_categories")
