"""initial catalog tables

Revision ID: 0001
Revises:
Create Date: 2026-09-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_categories",
        sa.Column("slug", sa.String(120), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
    )

    op.create_table(
        "catalog_products",
        sa.Column("sku", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "category_slug",
            sa.String(120),
            sa.ForeignKey("catalog_categories.slug"),
            nullable=False,
        ),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_currency", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("original_price_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "images", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
    )
    op.create_index(
        "ix_catalog_products_category_slug", "catalog_products", ["category_slug"]
    )

    op.create_table(
        "catalog_product_variants",
        sa.Column("sku", sa.String(64), primary_key=True),
        sa.Column(
            "product_sku", sa.String(64), sa.ForeignKey("catalog_products.sku"), nullable=False
        ),
        sa.Column("size", sa.String(20), nullable=False),
        sa.Column("color", sa.String(60), nullable=False),
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_catalog_variants_product_sku", "catalog_product_variants", ["product_sku"]
    )


def downgrade() -> None:
    op.drop_table("catalog_product_variants")
    op.drop_table("catalog_products")
    op.drop_table("catalog_categories")
