"""Modelo SQLAlchemy do índice vetorial do catálogo (RAG, ADR-0011).

Vive só no adapter — core_ai_assistant não conhece SQLAlchemy nem pgvector,
só a porta ProductIndex.
"""
from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adapters_persistence.db import Base

# Mesma dimensão do text-embedding-3-small (Azure OpenAI) — ver
# adapters_external.ai.dev_llm_provider.EMBEDDING_DIMENSIONS e ADR-0011.
EMBEDDING_DIMENSIONS = 1536


class ProductIndexModel(Base):
    __tablename__ = "ai_assistant_product_index"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
