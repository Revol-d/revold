"""Implementação Redis da porta core_identity.ports.RateLimiter (ADR-0016).

Janela fixa (fixed window counter), não token bucket "de verdade" — mais
simples de implementar corretamente com só INCR+EXPIRE, e suficiente para
proteger a API pública de abuso: cada chamador (`principal_id`) tem seu
próprio contador, que expira sozinho no fim da janela, sem job de limpeza.
"""
from __future__ import annotations

from redis.asyncio import Redis


class RedisRateLimiter:
    """Implementa core_identity.ports.RateLimiter."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, principal_id: str, *, window_seconds: int) -> str:
        # O próprio window_seconds faz parte da chave: se o limite mudar de
        # configuração, o contador antigo não "vaza" pra janela nova com
        # duração diferente.
        return f"ratelimit:{principal_id}:{window_seconds}"

    async def allow(self, principal_id: str, *, limit: int, window_seconds: int) -> bool:
        key = self._key(principal_id, window_seconds=window_seconds)
        count = await self._redis.incr(key)
        if count == 1:
            # Só a primeira chamada da janela define o TTL — chamadas
            # seguintes não devem "empurrar" o expiration pra frente
            # (senão um chamador contínuo nunca deixaria a janela expirar).
            await self._redis.expire(key, window_seconds)
        return count <= limit
