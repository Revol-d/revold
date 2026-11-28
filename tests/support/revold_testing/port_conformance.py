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

from revold_inventory.ports import InventoryRepository
from revold_orders.domain import Money, Order, OrderLine, PaymentStatus
from revold_orders.ports import OrderRepository
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
