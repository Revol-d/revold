"""Testes de integração do AzureSqlProductIndexRepository (RAG, ADR-0011)
contra um Azure SQL/SQL Server real -- mesma convenção do teste Postgres irmão
(test_product_index_repository_integration.py): pula sozinho se
TEST_DATABASE_URL_AZURE_SQL/DATABASE_URL_AZURE_SQL não apontar pra um banco
alcançável.

Chama a MESMA função de conformidade que o teste Postgres chama -- prova
mecânica de que `VECTOR_DISTANCE('cosine', ...)` (Azure SQL/DiskANN) se
comporta igual ao `cosine_distance()` do pgvector.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_ai_assistant.adapters.azure_sql.repository import AzureSqlProductIndexRepository
from revold_testing.port_conformance import assert_product_index_conformance

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL_AZURE_SQL",
    os.environ.get(
        "DATABASE_URL_AZURE_SQL",
        "mssql+aioodbc://sa:revold_dev_only_1@localhost:1433/revold"
        "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
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
        pytest.skip(f"Azure SQL de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text("TRUNCATE TABLE ai_assistant_product_index"))
        await session.commit()
        yield AzureSqlProductIndexRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_product_index(repository) -> None:
    await assert_product_index_conformance(repository)
