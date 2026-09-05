from __future__ import annotations

from decimal import Decimal

import pytest
from fakeredis import FakeAsyncRedis

from adapters_persistence.cart.redis_repository import RedisCartRepository
from core_cart.domain import Cart, Money


@pytest.fixture
async def repository():
    fake_redis = FakeAsyncRedis()
    yield RedisCartRepository(fake_redis)
    await fake_redis.aclose()


async def test_get_carrinho_inexistente_retorna_none(repository):
    assert await repository.get("nao-existe") is None


async def test_save_e_get_roundtrip(repository):
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("79.90")), quantity=2)

    await repository.save(cart)
    reloaded = await repository.get("c1")

    assert reloaded is not None
    assert reloaded.cart_id == "c1"
    assert len(reloaded.items) == 1
    assert reloaded.items[0].sku == "A"
    assert reloaded.items[0].unit_price.amount == Decimal("79.90")
    assert reloaded.total().amount == Decimal("159.80")


async def test_delete_remove_carrinho(repository):
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("10")))
    await repository.save(cart)

    await repository.delete("c1")

    assert await repository.get("c1") is None
