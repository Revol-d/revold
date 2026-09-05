"""Injeção de dependência do api-gateway.

O api-gateway é a única camada que conhece FastAPI + a implementação
concreta dos adapters. Os cores nunca são importados fora daqui a não ser
pelas suas portas e casos de uso.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from core_catalog.ports import ProductRepository

_engine = make_engine()
_session_factory = make_session_factory(_engine)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session


async def get_product_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProductRepository:
    return PostgresProductRepository(session)
