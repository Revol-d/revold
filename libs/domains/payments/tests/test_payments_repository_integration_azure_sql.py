"""Testes de integração do AzureSqlChargeRepository contra um Azure SQL/SQL Server
real -- pula sozinho se TEST_DATABASE_URL/DATABASE_URL não apontar pra um banco
alcançável.

Chama a função de conformidade compartilhada da porta (ver
tests/support/revold_testing/port_conformance.py).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_payments.adapters.azure_sql.repository import AzureSqlChargeRepository
from revold_testing.port_conformance import assert_charge_repository_conformance

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
        await session.execute(text("TRUNCATE TABLE payment_charges"))
        await session.commit()
        yield AzureSqlChargeRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_charge_repository(repository) -> None:
    await assert_charge_repository_conformance(repository)
