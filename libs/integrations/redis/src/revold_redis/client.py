"""Fábrica do client Redis assíncrono."""

from __future__ import annotations

from redis.asyncio import Redis


def make_redis_client(redis_url: str) -> Redis:
    """Cria o cliente. A URL vem do `settings.py` do app, nunca do ambiente daqui."""
    return Redis.from_url(redis_url, decode_responses=True)
