from __future__ import annotations

import pytest
from fakeredis import FakeAsyncRedis

from adapters_persistence.identity.redis_rate_limiter import RedisRateLimiter


@pytest.fixture
async def limiter():
    fake_redis = FakeAsyncRedis()
    yield RedisRateLimiter(fake_redis)
    await fake_redis.aclose()


async def test_permite_ate_o_limite(limiter):
    for _ in range(3):
        assert await limiter.allow("parceiro-1", limit=3, window_seconds=60) is True


async def test_bloqueia_acima_do_limite(limiter):
    for _ in range(3):
        await limiter.allow("parceiro-1", limit=3, window_seconds=60)

    assert await limiter.allow("parceiro-1", limit=3, window_seconds=60) is False


async def test_cada_principal_tem_seu_proprio_contador(limiter):
    for _ in range(3):
        await limiter.allow("parceiro-1", limit=3, window_seconds=60)

    # parceiro-2 não é afetado pelo consumo de parceiro-1
    assert await limiter.allow("parceiro-2", limit=3, window_seconds=60) is True


async def test_janela_expira_e_libera_de_novo(limiter):
    for _ in range(2):
        await limiter.allow("parceiro-1", limit=2, window_seconds=60)
    assert await limiter.allow("parceiro-1", limit=2, window_seconds=60) is False

    # simula o fim da janela apagando a chave diretamente (equivalente a
    # esperar o TTL expirar, sem precisar de sleep real no teste)
    await limiter._redis.delete(limiter._key("parceiro-1", window_seconds=60))

    assert await limiter.allow("parceiro-1", limit=2, window_seconds=60) is True
