"""Modelo SQLAlchemy do índice vetorial do catálogo (RAG, ADR-0011) no Azure SQL.

Vive só no adapter -- revold_ai_assistant não conhece SQLAlchemy nem o tipo
VECTOR, só a porta ProductIndex. Espelha adapters/postgres/models.py, trocando
pgvector.sqlalchemy.Vector pelo tipo customizado em
adapters/azure_sql/vector_type.py (SQLAlchemy ainda não tem suporte nativo ao
VECTOR do Azure SQL).
"""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from revold_ai_assistant.adapters.azure_sql.vector_type import Vector
from revold_azure_sql.db import Base

EMBEDDING_DIMENSIONS = 1536


class ProductIndexModel(Base):
    __tablename__ = "ai_assistant_product_index"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
