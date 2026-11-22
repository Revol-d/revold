"""Testes de integração do AzureSqlInventoryRepository contra um Azure SQL/SQL Server
real -- mesma convenção do teste Postgres irmão
(test_inventory_repository_integration.py): pula sozinho se
TEST_DATABASE_URL_AZURE_SQL/DATABASE_URL_AZURE_SQL não apontar pra um banco alcançável.

Chama a MESMA função de conformidade que o teste Postgres chama -- prova mecânica de
que os dois adapters se comportam igual (ver
tests/support/revold_testing/port_conformance.py).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_inventory.adapters.azure_sql.repository import AzureSqlInventoryRepository
from revold_inventory.domain import StockLevel
from revold_testing.port_conformance import assert_inventory_repository_conformance

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
        await session.execute(text("TRUNCATE TABLE inventory_stock_levels"))
        await session.commit()
        yield AzureSqlInventoryRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_inventory_repository(repository) -> None:
    await assert_inventory_repository_conformance(repository)


@pytest.mark.parametrize(
    ("primeiro_sku", "segundo_sku"),
    [("abc-1", "ABC-1"), ("SKU-日本", "SKU-中国")],
)
async def test_skus_diferentes_nao_compartilham_estoque(
    repository, primeiro_sku: str, segundo_sku: str
) -> None:
    # Com a colação padrão do servidor (case-insensitive, CP1252), `ABC-1` encontra a
    # linha de `abc-1` e sobrescreve o estoque dela, sem erro. O mesmo acontece com SKUs
    # fora do CP1252, que viram `?` ao gravar. A releitura usa uma sessão nova porque a
    # sessão que gravou devolveria o objeto em memória (`expire_on_commit=False`).
    await repository.save(StockLevel(sku=primeiro_sku, quantity_on_hand=10, quantity_reserved=0))
    await repository.save(StockLevel(sku=segundo_sku, quantity_on_hand=3, quantity_reserved=0))

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as fresh_session:
        fresh_repository = AzureSqlInventoryRepository(fresh_session)
        primeiro = await fresh_repository.get(primeiro_sku)
        segundo = await fresh_repository.get(segundo_sku)
    await engine.dispose()

    assert primeiro is not None
    assert segundo is not None
    assert (primeiro.sku, primeiro.quantity_on_hand) == (primeiro_sku, 10)
    assert (segundo.sku, segundo.quantity_on_hand) == (segundo_sku, 3)
