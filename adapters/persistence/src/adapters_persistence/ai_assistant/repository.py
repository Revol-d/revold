"""Implementação Postgres+pgvector da porta core_ai_assistant.ports.ProductIndex.

Note que este módulo importa core_ai_assistant (a porta que implementa) mas
core_ai_assistant nunca importa este módulo — a dependência aponta numa via
só, de fora para dentro (Clean/Hexagonal, ver ADR-0002).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters_persistence.ai_assistant.models import ProductIndexModel
from core_ai_assistant.domain import RetrievedProduct


class PostgresProductIndexRepository:
    """Implementa core_ai_assistant.ports.ProductIndex via SQLAlchemy async.

    Escreve — por isso commita a própria transação em `upsert`, no mesmo
    espírito do PostgresInventoryRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, *, sku: str, name: str, description: str, embedding: list[float]
    ) -> None:
        model = await self._session.get(ProductIndexModel, sku)
        if model is None:
            model = ProductIndexModel(sku=sku)
            self._session.add(model)
        model.name = name
        model.description = description
        model.embedding = embedding
        await self._session.commit()

    async def search(self, *, embedding: list[float], limit: int) -> list[RetrievedProduct]:
        distance = ProductIndexModel.embedding.cosine_distance(embedding).label("distance")
        stmt = (
            select(ProductIndexModel, distance)
            .order_by(distance)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            RetrievedProduct(sku=model.sku, name=model.name, distance=float(dist))
            for model, dist in result.all()
        ]
