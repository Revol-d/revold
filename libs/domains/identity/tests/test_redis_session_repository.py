from __future__ import annotations

import pytest
from fakeredis import FakeAsyncRedis

from revold_identity.adapters.redis.session_repository import RedisSessionRepository
from revold_identity.domain import AuthenticatedUser, Role


@pytest.fixture
async def repository():
    fake_redis = FakeAsyncRedis()
    yield RedisSessionRepository(fake_redis)
    await fake_redis.aclose()


def _sample_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        external_id="ext-1",
        provider="dev",
        email="nick@example.com",
        name="Nick",
        roles=(Role.CUSTOMER, Role.ADMIN),
    )


async def test_get_sessao_inexistente_retorna_none(repository):
    assert await repository.get("nao-existe") is None


async def test_create_e_get_roundtrip(repository):
    user = _sample_user()

    session_id = await repository.create(user)
    reloaded = await repository.get(session_id)

    assert reloaded is not None
    assert reloaded == user


async def test_create_gera_ids_diferentes_a_cada_chamada(repository):
    user = _sample_user()
    id_a = await repository.create(user)
    id_b = await repository.create(user)
    assert id_a != id_b


async def test_delete_remove_sessao(repository):
    session_id = await repository.create(_sample_user())

    await repository.delete(session_id)

    assert await repository.get(session_id) is None
