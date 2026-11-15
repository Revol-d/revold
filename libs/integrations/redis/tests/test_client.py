"""O cliente do Redis é montado a partir da URL recebida, sem abrir conexão."""

from __future__ import annotations

from redis.asyncio import Redis

from revold_redis.client import make_redis_client


def test_make_redis_client_uses_the_url_it_receives() -> None:
    client = make_redis_client("redis://cache.example:6380/2")

    assert isinstance(client, Redis)
    kwargs = client.connection_pool.connection_kwargs
    assert kwargs["host"] == "cache.example"
    assert kwargs["port"] == 6380
    assert kwargs["db"] == 2


def test_responses_are_decoded_to_text() -> None:
    """Os repositórios guardam JSON em texto: sem isto, `get` devolveria bytes."""
    client = make_redis_client("redis://cache.example:6379/0")

    assert client.connection_pool.connection_kwargs["decode_responses"] is True
