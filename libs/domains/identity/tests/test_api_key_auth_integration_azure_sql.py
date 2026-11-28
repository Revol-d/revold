"""Testes de integração do AzureSqlApiKeyAuth contra um Azure SQL/SQL Server real --
mesma convenção do teste Postgres irmão (test_api_key_auth_integration.py): pula
sozinho se TEST_DATABASE_URL_AZURE_SQL/DATABASE_URL_AZURE_SQL não apontar pra um banco
alcançável.

Chama a MESMA função de conformidade que o teste Postgres chama.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_identity.adapters.azure_sql.api_key_auth import AzureSqlApiKeyAuth
from revold_testing.port_conformance import assert_api_key_auth_conformance

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
async def auth():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — qualquer falha de conexão vira skip
        await engine.dispose()
        pytest.skip(f"Azure SQL de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text("TRUNCATE TABLE identity_api_keys"))
        await session.commit()
        yield AzureSqlApiKeyAuth(session)
    await engine.dispose()


async def test_conformidade_da_porta_api_key_auth(auth) -> None:
    await assert_api_key_auth_conformance(auth)


async def test_texto_fora_do_cp1252_sobrevive_numa_sessao_nova(auth) -> None:
    # Mesmo achado de revisão do store-settings: VARCHAR com a colação padrão do
    # servidor troca caractere fora do CP1252 por `?` ao gravar, sem erro. `issue()`
    # devolve o nome a partir do objeto já em memória (não mascara nada aqui), por
    # isso relê via `resolve()` numa sessão/engine nova, que é o caminho real que
    # outro request usaria.
    nome_com_emoji = "Parceiro ERP 🤝"
    _, raw_key = await auth.issue(name=nome_com_emoji)

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as fresh_session:
        resolved = await AzureSqlApiKeyAuth(fresh_session).resolve(raw_key)
    await engine.dispose()

    assert resolved is not None
    assert resolved.name == nome_com_emoji


async def test_issue_grava_so_o_hash_nunca_o_texto_puro(auth) -> None:
    principal, raw_key = await auth.issue(name="Parceiro ERP")

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT key_hash FROM identity_api_keys WHERE key_id = :id"),
                {"id": principal.key_id},
            )
        ).one()
        assert raw_key not in row[0]
    await engine.dispose()
