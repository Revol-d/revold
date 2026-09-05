"""Fábrica do client Redis assíncrono, compartilhada pelos adapters que
precisarem dele (hoje só core-cart)."""
from __future__ import annotations

import os

from redis.asyncio import Redis


def make_redis_client(redis_url: str | None = None) -> Redis:
    url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(url, decode_responses=True)
