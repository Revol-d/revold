"""Testes de integração do PostgresProductIndexRepository (RAG, ADR-0011)
contra um Postgres real com pgvector — igual espírito de
test_catalog_repository_integration.py, mas para o índice vetorial.

A conformidade geral chama a função compartilhada em
tests/support/revold_testing/port_conformance.py, que
test_product_index_repository_integration_azure_sql.py também chama -- prova
mecânica de que `cosine_distance()` (pgvector) e `VECTOR_DISTANCE('cosine',
...)` (Azure SQL/DiskANN) se comportam igual.

Pula (skip) automaticamente se TEST_DATABASE_URL/DATABASE_URL não apontar
pra um Postgres alcançável.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_ai_assistant.adapters.postgres.repository import PostgresProductIndexRepository
from revold_testing.port_conformance import assert_product_index_conformance

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
    ),
)


@pytest.fixture
async def repository():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — qualquer falha de conexão vira skip
        await engine.dispose()
        pytest.skip(f"Postgres de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text("TRUNCATE ai_assistant_product_index RESTART IDENTITY CASCADE"))
        await session.commit()
        yield PostgresProductIndexRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_product_index(repository) -> None:
    """Prova mecânica de que o adapter Postgres satisfaz a mesma porta que o
    adapter Azure SQL (test_product_index_repository_integration_azure_sql.py
    chama a mesma função)."""
    await assert_product_index_conformance(repository)
