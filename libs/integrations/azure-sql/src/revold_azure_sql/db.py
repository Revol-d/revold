"""Configuração de engine/sessão SQLAlchemy compartilhada pelos adapters de persistência."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> AsyncEngine:
    """Cria o engine assíncrono. A URL vem do `settings.py` do app, nunca do ambiente daqui.

    Espera uma URL `mssql+aioodbc://...` com o driver ODBC na query string (ex.:
    `?driver=ODBC+Driver+17+for+SQL+Server`) -- quem monta essa URL é `settings.py`.
    """
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
