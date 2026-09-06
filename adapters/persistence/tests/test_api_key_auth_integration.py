"""Testes de integração do PostgresApiKeyAuth (ADR-0016) contra um Postgres
real — mesma convenção de test_ai_assistant_repository_integration.py: pula
sozinho se TEST_DATABASE_URL/DATABASE_URL não apontar pra um Postgres
alcançável.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from adapters_persistence.identity.postgres_api_key_auth import PostgresApiKeyAuth
from core_identity.domain import ApiKeyNotFound

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
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
        pytest.skip(f"Postgres de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text("TRUNCATE identity_api_keys RESTART IDENTITY CASCADE"))
        await session.commit()
        yield PostgresApiKeyAuth(session)
    await engine.dispose()


async def test_issue_grava_so_o_hash_nunca_o_texto_puro(auth) -> None:
    principal, raw_key = await auth.issue(name="Parceiro ERP")

    assert raw_key.startswith("rvld_")
    assert principal.name == "Parceiro ERP"

    # confirma via uma conexão independente que a tabela não guarda o texto
    # puro em lugar nenhum
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        row = (
            await conn.execute(text("SELECT key_hash FROM identity_api_keys WHERE key_id = :id"), {"id": principal.key_id})
        ).one()
        assert raw_key not in row[0]
    await engine.dispose()


async def test_resolve_de_chave_valida_devolve_o_principal(auth) -> None:
    principal, raw_key = await auth.issue(name="Parceiro ERP")

    resolved = await auth.resolve(raw_key)

    assert resolved == principal


async def test_resolve_de_chave_inexistente_devolve_none(auth) -> None:
    assert await auth.resolve("rvld_nao-existe") is None


async def test_resolve_de_chave_revogada_devolve_none(auth) -> None:
    principal, raw_key = await auth.issue(name="Parceiro ERP")

    await auth.revoke(principal.key_id)

    assert await auth.resolve(raw_key) is None


async def test_revoke_de_key_id_inexistente_levanta_erro(auth) -> None:
    with pytest.raises(ApiKeyNotFound):
        await auth.revoke("nao-existe")


async def test_issue_gera_chaves_diferentes_a_cada_chamada(auth) -> None:
    _, raw_key_1 = await auth.issue(name="Parceiro A")
    _, raw_key_2 = await auth.issue(name="Parceiro B")

    assert raw_key_1 != raw_key_2
