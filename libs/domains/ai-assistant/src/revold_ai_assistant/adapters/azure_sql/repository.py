"""Implementação Azure SQL da porta revold_ai_assistant.ports.ProductIndex.

Usa `VECTOR_DISTANCE('cosine', ...)` -- a função nativa do Azure SQL para
distância de cosseno.

O vetor (seja no INSERT/UPDATE, seja na busca) entra como LITERAL SQL
(`CAST('[...]' AS VECTOR(n))`), não como bind parameter -- testado e
confirmado nos dois casos: o pyodbc manda um parâmetro longo (1536 floats
vira uma string de ~7400 caracteres) como `ntext` por padrão, e tanto o
`INSERT`/`UPDATE` direto na coluna `VECTOR` quanto o `VECTOR_DISTANCE`
recusam ntext ("Operand type clash: ntext is incompatible with vector" /
"Explicit conversion from data type ntext to vector is not allowed").
Forçar o tipo via `cursor.setinputsizes()` (o jeito "certo" no pyodbc puro)
também falhou aqui (erro de precisão inválida) -- diferente do caso do
catalog (termo de busca textual), aqui não há risco de injeção real: o
literal é sempre uma lista de `float` formatada por este código, nunca texto
de usuário. Por isso o `upsert` usa SQL cru (`text()`) para sku/name/
description (parâmetros normais, sem problema) + o literal só para
`embedding`, em vez do padrão ORM (`session.get` + atributo) usado nos outros
adapters desta migração.
"""
from __future__ import annotations

import json

from sqlalchemy import func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from revold_ai_assistant.adapters.azure_sql.models import EMBEDDING_DIMENSIONS, ProductIndexModel
from revold_ai_assistant.domain import RetrievedProduct


def _vector_literal(embedding: list[float]) -> str:
    values = json.dumps([float(x) for x in embedding])
    return f"CAST('{values}' AS VECTOR({EMBEDDING_DIMENSIONS}))"


class AzureSqlProductIndexRepository:
    """Implementa revold_ai_assistant.ports.ProductIndex via SQLAlchemy async
    contra o Azure SQL Database. Escreve -- por isso commita a própria
    transação em `upsert`, no mesmo espírito do adapter Postgres."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, *, sku: str, name: str, description: str, embedding: list[float]
    ) -> None:
        vector_literal = _vector_literal(embedding)
        exists = await self._session.get(ProductIndexModel, sku)
        if exists is None:
            await self._session.execute(
                text(
                    # vector_literal vem de _vector_literal(), sempre uma lista de float
                    # formatada por este codigo (ver docstring do modulo), nunca texto de
                    # usuario; sku/name/description continuam bind parameter
                    "INSERT INTO ai_assistant_product_index (sku, name, description, embedding) "  # nosec B608
                    f"VALUES (:sku, :name, :description, {vector_literal})"
                ),
                {"sku": sku, "name": name, "description": description},
            )
        else:
            await self._session.execute(
                text(
                    # mesma justificativa do INSERT acima
                    "UPDATE ai_assistant_product_index "  # nosec B608
                    f"SET name = :name, description = :description, embedding = {vector_literal} "
                    "WHERE sku = :sku"
                ),
                {"sku": sku, "name": name, "description": description},
            )
        await self._session.commit()

    async def search(self, *, embedding: list[float], limit: int) -> list[RetrievedProduct]:
        distance = func.VECTOR_DISTANCE(
            literal_column("'cosine'"),
            ProductIndexModel.embedding,
            literal_column(_vector_literal(embedding)),
        ).label("distance")
        stmt = select(ProductIndexModel, distance).order_by(distance).limit(limit)
        result = await self._session.execute(stmt)
        return [
            RetrievedProduct(sku=model.sku, name=model.name, distance=float(dist))
            for model, dist in result.all()
        ]
