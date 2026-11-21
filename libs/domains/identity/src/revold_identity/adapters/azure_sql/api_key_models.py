"""Modelo SQLAlchemy de API key no Azure SQL. Vive só no adapter -- revold_identity
não o conhece.

Espelha adapters/postgres/api_key_models.py: mesma tabela. `DateTime(timezone=True)`
mapeia para DATETIMEOFFSET no dialeto mssql (verificado via autogenerate contra um
SQL Server real antes de aplicar) -- a única coluna desta migração que não é um tipo
simples de string.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from revold_azure_sql.db import Base


class ApiKeyModel(Base):
    __tablename__ = "identity_api_keys"
    __table_args__ = (UniqueConstraint("key_hash", name="identity_api_keys_key_hash_key"),)

    key_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
