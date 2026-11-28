"""Testes de integração do PostgresOrderRepository (ADR-0023) contra um
Postgres real — mesma convenção de test_store_settings_repository_integration.py:
pula sozinho se TEST_DATABASE_URL/DATABASE_URL não apontar pra um Postgres
alcançável.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_orders.adapters.postgres.repository import PostgresOrderRepository
from revold_testing.port_conformance import assert_order_repository_conformance

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
        await session.execute(text("TRUNCATE order_lines, orders"))
        await session.commit()
        yield PostgresOrderRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_order_repository(repository) -> None:
    """Prova mecânica de que o adapter Postgres satisfaz a mesma porta que o adapter
    Azure SQL (test_orders_repository_integration_azure_sql.py chama a mesma
    função)."""
    await assert_order_repository_conformance(repository)
