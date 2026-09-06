"""Modelo SQLAlchemy de API key. Vive só no adapter — core_identity não o
conhece (ADR-0002, ADR-0016)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from adapters_persistence.db import Base


class ApiKeyModel(Base):
    __tablename__ = "identity_api_keys"

    key_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # sha256 hex digest — nunca o texto puro (ver PostgresApiKeyAuth.issue).
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
