"""Testes de integração do AzureSqlOrderRepository contra um Azure SQL/SQL Server
real -- mesma convenção do teste Postgres irmão
(test_orders_repository_integration.py): pula sozinho se
TEST_DATABASE_URL_AZURE_SQL/DATABASE_URL_AZURE_SQL não apontar pra um banco alcançável.

Chama a MESMA função de conformidade que o teste Postgres chama.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_orders.adapters.azure_sql.repository import AzureSqlOrderRepository
from revold_testing.port_conformance import assert_order_repository_conformance

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
        # SQL Server recusa TRUNCATE em tabela referenciada por FK, mesmo vazia
        # (testado e confirmado: "Cannot truncate table ... FOREIGN KEY constraint") --
        # diferente do Postgres, que só pede TRUNCATE order_lines, orders juntos.
        await session.execute(text("DELETE FROM order_lines"))
        await session.execute(text("DELETE FROM orders"))
        await session.commit()
        yield AzureSqlOrderRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_order_repository(repository) -> None:
    await assert_order_repository_conformance(repository)
