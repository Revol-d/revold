"""Testes de integração do AzureSqlProductIndexRepository (RAG, ADR-0011)
contra um Azure SQL/SQL Server real -- pula sozinho se
TEST_DATABASE_URL/DATABASE_URL não apontar pra um banco alcançável.

Chama a função de conformidade compartilhada da porta (ver
tests/support/revold_testing/port_conformance.py).
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
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
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


async def test_texto_fora_do_cp1252_sobrevive_numa_sessao_nova(repository) -> None:
    # Mesmo achado de revisão do store-settings: VARCHAR/TEXT com a colação
    # padrão do servidor trocam caractere fora do CP1252 por `?` ao gravar, sem
    # erro. O `upsert` grava via SQL cru, não ORM (ver repository.py) -- o
    # risco de mascaramento por sessão/identity map não existe aqui, mas o
    # teste relê numa sessão/engine nova mesmo assim, pra ficar explícito.
    embedding = [0.0] * 1536
    embedding[0] = 1.0
    await repository.upsert(
        sku="CAM-EMOJI",
        name="Camiseta 🛍️",
        description="Descrição com emoji 🎉 e acento: coração",
        embedding=embedding,
    )

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as fresh_session:
        resultados = await AzureSqlProductIndexRepository(fresh_session).search(
            embedding=embedding, limit=1
        )
        description = (
            await fresh_session.execute(
                text("SELECT description FROM ai_assistant_product_index WHERE sku = 'CAM-EMOJI'")
            )
        ).scalar_one()
    await engine.dispose()

    assert resultados[0].name == "Camiseta 🛍️"
    assert description == "Descrição com emoji 🎉 e acento: coração"
