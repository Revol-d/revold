"""Testes de integração do PostgresStoreSettingsRepository (ADR-0019) contra
um Postgres real — mesma convenção de test_api_key_auth_integration.py: pula
sozinho se TEST_DATABASE_URL/DATABASE_URL não apontar pra um Postgres
alcançável.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_store_settings.adapters.postgres.repository import PostgresStoreSettingsRepository
from revold_store_settings.domain import StoreSettings
from revold_testing.port_conformance import assert_store_settings_repository_conformance

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
        await session.execute(text("TRUNCATE store_settings"))
        await session.commit()
        yield PostgresStoreSettingsRepository(session)
    await engine.dispose()


async def test_conformidade_da_porta_store_settings_repository(repository) -> None:
    """Prova mecânica de que o adapter Postgres satisfaz a mesma porta que o adapter
    Azure SQL (test_store_settings_repository_integration_azure_sql.py chama a
    mesma função) -- ver tests/support/revold_testing/port_conformance.py."""
    await assert_store_settings_repository_conformance(repository)


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
