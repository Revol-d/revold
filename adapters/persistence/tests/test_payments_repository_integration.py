"""Testes de integração do PostgresChargeRepository (ADR-0024) contra um
Postgres real — mesma convenção de test_orders_repository_integration.py:
pula sozinho se TEST_DATABASE_URL/DATABASE_URL não apontar pra um Postgres
alcançável.
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from adapters_persistence.payments.repository import PostgresChargeRepository
from core_payments.domain import Charge, ChargeStatus, Money, PaymentMethod

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
    ),
)


def _charge(charge_id: str = "ch1", order_id: str = "o1") -> Charge:
    return Charge(
        charge_id=charge_id,
        order_id=order_id,
        provider="mercado_pago",
        provider_charge_id=f"mp-{charge_id}",
        method=PaymentMethod.PIX,
        amount=Money(Decimal("59.90")),
        pix_qr_code="qr-fake",
        pix_copy_paste="copia-e-cola-fake",
        created_at="2026-09-12T10:00:00+00:00",
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
        await session.execute(text("TRUNCATE payment_charges"))
        await session.commit()
        yield PostgresChargeRepository(session)
    await engine.dispose()


async def test_get_devolve_none_quando_nao_existe(repository) -> None:
    assert await repository.get("nao-existe") is None


async def test_save_depois_get_devolve_cobranca(repository) -> None:
    charge = _charge()
    await repository.save(charge)

    reloaded = await repository.get(charge.charge_id)

    assert reloaded is not None
    assert reloaded.order_id == "o1"
    assert reloaded.amount == Money(Decimal("59.90"))
    assert reloaded.status == ChargeStatus.PENDING
    assert reloaded.pix_qr_code == "qr-fake"


async def test_get_by_order_devolve_cobranca_mais_recente(repository) -> None:
    first = _charge("ch1", "o1")
    first.created_at = "2026-09-12T10:00:00+00:00"
    await repository.save(first)

    second = _charge("ch2", "o1")
    second.created_at = "2026-09-12T11:00:00+00:00"
    await repository.save(second)

    reloaded = await repository.get_by_order("o1")
    assert reloaded is not None
    assert reloaded.charge_id == "ch2"


async def test_get_by_provider_charge_id_encontra_cobranca(repository) -> None:
    charge = _charge()
    await repository.save(charge)

    reloaded = await repository.get_by_provider_charge_id("mp-ch1")
    assert reloaded is not None
    assert reloaded.charge_id == "ch1"


async def test_save_novamente_atualiza_status_sem_duplicar(repository) -> None:
    charge = _charge()
    await repository.save(charge)

    charge.mark_paid()
    await repository.save(charge)

    reloaded = await repository.get(charge.charge_id)
    assert reloaded is not None
    assert reloaded.status == ChargeStatus.PAID
