"""Testes de integração do PostgresOrderRepository (ADR-0023) contra um
Postgres real — mesma convenção de test_store_settings_repository_integration.py:
pula sozinho se TEST_DATABASE_URL/DATABASE_URL não apontar pra um Postgres
alcançável.
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_orders.adapters.postgres.repository import PostgresOrderRepository
from revold_orders.domain import Money, Order, OrderLine, PaymentStatus

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
    ),
)


def _order(order_id: str = "o1") -> Order:
    return Order(
        order_id=order_id,
        cart_id="c1",
        lines=(
            OrderLine(
                sku="A",
                product_name="Camiseta",
                variant_label="M / Azul",
                unit_price=Money(Decimal("59.90")),
                quantity=2,
            ),
            OrderLine(
                sku="B",
                product_name="Calça",
                variant_label="42",
                unit_price=Money(Decimal("120.00")),
                quantity=1,
            ),
        ),
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
        await session.execute(text("TRUNCATE order_lines, orders"))
        await session.commit()
        yield PostgresOrderRepository(session)
    await engine.dispose()


async def test_get_devolve_none_quando_nao_existe(repository) -> None:
    assert await repository.get("nao-existe") is None


async def test_save_depois_get_devolve_pedido_com_linhas_na_ordem_certa(repository) -> None:
    order = _order()
    await repository.save(order)

    reloaded = await repository.get(order.order_id)

    assert reloaded is not None
    assert reloaded.order_id == order.order_id
    assert [line.sku for line in reloaded.lines] == ["A", "B"]
    assert reloaded.total() == Money(Decimal("239.80"))
    assert reloaded.payment_status == PaymentStatus.PENDING


async def test_save_novamente_atualiza_status_sem_duplicar_linhas(repository) -> None:
    order = _order()
    await repository.save(order)

    order.mark_paid()
    await repository.save(order)

    reloaded = await repository.get(order.order_id)
    assert reloaded is not None
    assert reloaded.payment_status == PaymentStatus.PAID
    assert len(reloaded.lines) == 2  # não duplicou


async def test_list_filtra_por_payment_status_e_pagina(repository) -> None:
    paid = _order("o-pago")
    paid.mark_paid()
    await repository.save(paid)
    await repository.save(_order("o-pendente"))

    only_paid, total_paid = await repository.list(payment_status=PaymentStatus.PAID, page=1, page_size=20)
    assert total_paid == 1
    assert only_paid[0].order_id == "o-pago"

    all_orders, total_all = await repository.list(payment_status=None, page=1, page_size=1)
    assert total_all == 2
    assert len(all_orders) == 1
