"""API keys de parceiro/integração (ADR-0016)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_api_keys",
        sa.Column("key_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_identity_api_keys_key_hash", "identity_api_keys", ["key_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_identity_api_keys_key_hash", table_name="identity_api_keys")
    op.drop_table("identity_api_keys")
