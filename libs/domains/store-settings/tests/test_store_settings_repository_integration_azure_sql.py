"""Testes de integração do AzureSqlStoreSettingsRepository (ADR-0019) contra um Azure
SQL/SQL Server real — mesma convenção do teste Postgres irmão
(test_store_settings_repository_integration.py): pula sozinho se
TEST_DATABASE_URL_AZURE_SQL/DATABASE_URL não apontar pra um banco alcançável.

Chama a MESMA função de conformidade que o teste Postgres chama — prova mecânica de que
os dois adapters se comportam igual (ver tests/support/revold_testing/port_conformance.py
e o plano de migração Postgres -> Azure SQL, docs internos).
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_store_settings.adapters.azure_sql.repository import AzureSqlStoreSettingsRepository
from revold_store_settings.domain import StoreSettings
from revold_testing.port_conformance import assert_store_settings_repository_conformance

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
        await session.execute(text("TRUNCATE TABLE store_settings"))
        await session.commit()
        yield AzureSqlStoreSettingsRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_store_settings_repository(repository) -> None:
    await assert_store_settings_repository_conformance(repository)


async def test_texto_fora_do_cp1252_sobrevive_numa_sessao_nova(repository) -> None:
    # Achado de revisão: VARCHAR com a colação padrão do servidor
    # (SQL_Latin1_General_CP1_CI_AS) troca caractere fora do CP1252 por `?` ao
    # gravar, sem erro -- e a mesma sessão (`expire_on_commit=False`) mascara
    # isso, porque devolve o objeto já em memória em vez de reler do banco.
    # Por isso este teste abre uma sessão/engine NOVA pra reler, como o teste
    # de upsert logo abaixo já faz pra contar linhas.
    nome_com_emoji = "Nick Roupas 🛍️"
    await repository.save(
        StoreSettings(
            cnpj="",
            store_name=nome_com_emoji,
            contact_email="",
            contact_phone="",
            store_address="",
            low_stock_threshold=5,
        )
    )

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as fresh_session:
        reloaded = await AzureSqlStoreSettingsRepository(fresh_session).get()
    await engine.dispose()

    assert reloaded is not None
    assert reloaded.store_name == nome_com_emoji


async def test_save_duas_vezes_faz_upsert_no_mesmo_registro(repository) -> None:
    await repository.save(
        StoreSettings(
            cnpj="",
            store_name="Nick Roupas",
            contact_email="",
            contact_phone="",
            store_address="",
            low_stock_threshold=5,
        )
    )
    await repository.save(
        StoreSettings(
            cnpj="",
            store_name="Nick Roupas Ltda",
            contact_email="",
            contact_phone="",
            store_address="",
            low_stock_threshold=8,
        )
    )

    reloaded = await repository.get()

    assert reloaded is not None
    assert reloaded.store_name == "Nick Roupas Ltda"
    assert reloaded.low_stock_threshold == 8

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        count = (await conn.execute(text("SELECT COUNT(*) FROM store_settings"))).scalar_one()
        assert count == 1
    await engine.dispose()
