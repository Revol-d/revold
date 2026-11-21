"""Testes de integração do PostgresInventoryRepository contra um Postgres real --
mesma convenção de test_store_settings_repository_integration.py: pula sozinho se
TEST_DATABASE_URL/DATABASE_URL não apontar pra um Postgres alcançável.

Não existia antes desta migração (gap pré-existente, fechado aqui junto com o adapter
Azure SQL -- ver tests/support/revold_testing/port_conformance.py).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_inventory.adapters.postgres.repository import PostgresInventoryRepository
from revold_testing.port_conformance import assert_inventory_repository_conformance

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
        await session.execute(text("TRUNCATE inventory_stock_levels"))
        await session.commit()
        yield PostgresInventoryRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_inventory_repository(repository) -> None:
    """Prova mecânica de que o adapter Postgres satisfaz a mesma porta que o adapter
    Azure SQL (test_inventory_repository_integration_azure_sql.py chama a mesma
    função)."""
    await assert_inventory_repository_conformance(repository)
