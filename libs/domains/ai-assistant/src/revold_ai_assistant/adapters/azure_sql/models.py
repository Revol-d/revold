"""Modelo SQLAlchemy do índice vetorial do catálogo (RAG, ADR-0011) no Azure SQL.

Vive só no adapter -- revold_ai_assistant não conhece SQLAlchemy nem o tipo
VECTOR, só a porta ProductIndex. Usa o tipo customizado em
adapters/azure_sql/vector_type.py (SQLAlchemy ainda não tem suporte nativo ao
VECTOR do Azure SQL).

Sem índice `CREATE VECTOR INDEX` (DiskANN) de propósito -- testado e
confirmado que a versão do índice com suporte a DML (INSERT/UPDATE/DELETE
contínuos, o que o `upsert` desta porta precisa) só está GA no Azure SQL
Database/Fabric real; mesmo um SQL Server 2025 RTM-CU11 em caixa cria a
versão antiga, que torna a tabela somente-leitura assim que o índice existe
(`ALLOW_STALE_VECTOR_INDEX`, a válvula de escape documentada, nem é
reconhecida nessa build). `VECTOR_DISTANCE` funciona normalmente sem índice
(scan completo) -- mais lento em escala, mas idêntico em qualquer ambiente, e
sem essa trava de escrita. Criar o índice fica para quando a versão
DML-friendly estiver disponível de forma confiável (tarefa operacional
futura, fora desta migração).

`name`/`description` usam `Unicode`/`UnicodeText` (`NVARCHAR`/`NTEXT`), não
`String`/`Text` (`VARCHAR`/`TEXT`) -- achado de revisão do store-settings:
`VARCHAR`/`TEXT` com a colação padrão do servidor trocam caractere fora do
CP1252 por `?` ao gravar, sem erro.
"""
from __future__ import annotations

from sqlalchemy import String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column

from revold_ai_assistant.adapters.azure_sql.vector_type import Vector
from revold_azure_sql.db import Base

EMBEDDING_DIMENSIONS = 1536


class ProductIndexModel(Base):
    __tablename__ = "ai_assistant_product_index"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    description: Mapped[str] = mapped_column(UnicodeText, nullable=False, default="")
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
