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

from revold_inventory.ports import InventoryRepository
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
