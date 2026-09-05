"""Configuração de engine/sessão SQLAlchemy compartilhada pelos adapters de persistência."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    url = database_url or os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
    )
    return create_async_engine(url, echo=False, pool_pre_ping=True)


def make_session_factory(engine=None) -> async_sessionmaker[AsyncSession]:
    engine = engine or make_engine()
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
