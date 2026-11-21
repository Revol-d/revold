"""Funções de conformidade de porta: uma função por porta tocada pela migração
Postgres -> Azure SQL (ver o plano em docs internos), que QUALQUER adapter que diz
implementar aquela porta precisa passar. É a prova mecânica de que dois adapters
diferentes (ou um fake) se comportam do mesmo jeito -- antes desta migração, nenhuma
porta do repositório tinha isso: cada adapter só tinha o próprio teste bespoke, e os
fakes de teste nunca eram verificados contra o adapter real.

Escopo: só as portas tocadas por esta migração, não um framework genérico para todas as
portas do repositório (over-engineering fora do que a migração precisa).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from revold_identity.domain import ApiKeyNotFound
from revold_identity.ports import ApiKeyAuth
from revold_inventory.ports import InventoryRepository
from revold_orders.domain import Money, Order, OrderLine, PaymentStatus
from revold_orders.ports import OrderRepository
from revold_payments.domain import Charge
from revold_payments.domain import Money as PaymentMoney
from revold_payments.domain import PaymentMethod
from revold_payments.ports import ChargeRepository
from revold_store_settings.ports import StoreSettingsRepository
from revold_testing.inventory_factories import StockLevelFactory
from revold_testing.store_settings_factories import StoreSettingsFactory


async def assert_store_settings_repository_conformance(
    repository: StoreSettingsRepository,
) -> None:
    """Qualquer StoreSettingsRepository (Postgres, Azure SQL, fake em memória)
    precisa passar por isto. Assume o repositório vazio ao receber (quem chama cuida
    de limpar o estado antes, ver as fixtures `repository` de cada teste de
    integração)."""
    assert await repository.get() is None

    first = StoreSettingsFactory()
    await repository.save(first)
    assert await repository.get() == first

    second = StoreSettingsFactory()
    await repository.save(second)
    reloaded = await repository.get()
    assert reloaded == second
    assert reloaded != first


async def assert_inventory_repository_conformance(repository: InventoryRepository) -> None:
    """Qualquer InventoryRepository (Postgres, Azure SQL, fake em memória) precisa
    passar por isto. Usa um SKU próprio (`StockLevelFactory` gera um aleatório) para
    não colidir com outros registros que já estejam no repositório."""
    stock = StockLevelFactory()

    assert await repository.get(stock.sku) is None

    await repository.save(stock)
    assert await repository.get(stock.sku) == stock

    stock.receive(10)
    await repository.save(stock)
    reloaded = await repository.get(stock.sku)
    assert reloaded == stock
    assert reloaded.quantity_on_hand == stock.quantity_on_hand


def _build_order(order_id: str) -> Order:
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


async def assert_order_repository_conformance(repository: OrderRepository) -> None:
    """Qualquer OrderRepository (Postgres, Azure SQL, fake em memória) precisa passar
    por isto. Assume o repositório vazio ao receber."""
    assert await repository.get("nao-existe") is None

    order = _build_order("o-pago")
    await repository.save(order)
    reloaded = await repository.get(order.order_id)
    assert reloaded is not None
    assert [line.sku for line in reloaded.lines] == ["A", "B"]
    assert reloaded.total() == Money(Decimal("239.80"))
    assert reloaded.payment_status == PaymentStatus.PENDING

    reloaded.mark_paid()
    await repository.save(reloaded)
    reloaded_again = await repository.get(order.order_id)
    assert reloaded_again is not None
    assert reloaded_again.payment_status == PaymentStatus.PAID
    assert len(reloaded_again.lines) == 2  # não duplicou

    await repository.save(_build_order("o-pendente"))

    only_paid, total_paid = await repository.list(
        payment_status=PaymentStatus.PAID, page=1, page_size=20
    )
    assert total_paid == 1
    assert only_paid[0].order_id == "o-pago"

    all_orders, total_all = await repository.list(payment_status=None, page=1, page_size=1)
    assert total_all == 2
    assert len(all_orders) == 1


def _build_charge(charge_id: str, order_id: str, *, created_at: str) -> Charge:
    return Charge(
        charge_id=charge_id,
        order_id=order_id,
        provider="mercado_pago",
        provider_charge_id=f"mp-{charge_id}",
        method=PaymentMethod.PIX,
        amount=PaymentMoney(Decimal("59.90")),
        pix_qr_code="qr-fake",
        pix_copy_paste="copia-e-cola-fake",
        created_at=created_at,
    )


async def assert_charge_repository_conformance(repository: ChargeRepository) -> None:
    """Qualquer ChargeRepository (Postgres, Azure SQL, fake em memória) precisa
    passar por isto. Assume o repositório vazio ao receber."""
    assert await repository.get("nao-existe") is None

    first = _build_charge("ch1", "o1", created_at="2026-09-12T10:00:00+00:00")
    await repository.save(first)
    reloaded = await repository.get(first.charge_id)
    assert reloaded is not None
    assert reloaded.order_id == "o1"
    assert reloaded.amount == PaymentMoney(Decimal("59.90"))
    assert reloaded.pix_qr_code == "qr-fake"

    second = _build_charge("ch2", "o1", created_at="2026-09-12T11:00:00+00:00")
    await repository.save(second)
    most_recent = await repository.get_by_order("o1")
    assert most_recent is not None
    assert most_recent.charge_id == "ch2"

    found = await repository.get_by_provider_charge_id("mp-ch1")
    assert found is not None
    assert found.charge_id == "ch1"

    reloaded.mark_paid()
    await repository.save(reloaded)
    reloaded_again = await repository.get(first.charge_id)
    assert reloaded_again is not None
    assert reloaded_again.status.value == "paid"


async def assert_api_key_auth_conformance(auth: ApiKeyAuth) -> None:
    """Qualquer ApiKeyAuth (Postgres, Azure SQL, fake em memória) precisa passar por
    isto."""
    principal, raw_key = await auth.issue(name="Parceiro ERP")
    assert raw_key.startswith("rvld_")
    assert principal.name == "Parceiro ERP"

    resolved = await auth.resolve(raw_key)
    assert resolved == principal

    assert await auth.resolve("rvld_nao-existe") is None

    await auth.revoke(principal.key_id)
    assert await auth.resolve(raw_key) is None

    with pytest.raises(ApiKeyNotFound):
        await auth.revoke("nao-existe")

    _, raw_key_a = await auth.issue(name="Parceiro A")
    _, raw_key_b = await auth.issue(name="Parceiro B")
    assert raw_key_a != raw_key_b
