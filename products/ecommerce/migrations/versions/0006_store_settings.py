"""Configuração da loja editável pela Nick (ADR-0019)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "store_settings",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("cnpj", sa.String(30), nullable=False, server_default=""),
        sa.Column("store_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("contact_email", sa.String(200), nullable=False, server_default=""),
        sa.Column("contact_phone", sa.String(30), nullable=False, server_default=""),
        sa.Column("store_address", sa.String(500), nullable=False, server_default=""),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_table("store_settings")
