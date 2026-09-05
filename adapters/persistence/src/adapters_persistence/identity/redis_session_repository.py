"""Implementação Redis da porta core_identity.ports.SessionRepository (ADR-0010).

Sessão é serializada como JSON com TTL (expira sozinha, sem job de
limpeza) sob a chave "session:{id}". O id é gerado com secrets.token_urlsafe
(aleatoriedade criptográfica) — é ele, e só ele, que viaja no cookie
HttpOnly do navegador; nenhum dado de usuário nem claim vai para o cliente.
"""
from __future__ import annotations

import json
import secrets

from redis.asyncio import Redis

from core_identity.domain import AuthenticatedUser, Role

_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 dias, mesma janela usada pelo carrinho


def _user_to_json(user: AuthenticatedUser) -> str:
    return json.dumps(
        {
            "external_id": user.external_id,
            "provider": user.provider,
            "email": user.email,
            "name": user.name,
            "roles": [role.value for role in user.roles],
        }
    )


def _user_from_json(raw: str) -> AuthenticatedUser:
    data = json.loads(raw)
    return AuthenticatedUser(
        external_id=data["external_id"],
        provider=data["provider"],
        email=data["email"],
        name=data["name"],
        roles=tuple(Role(role) for role in data["roles"]),
    )


class RedisSessionRepository:
    """Implementa core_identity.ports.SessionRepository."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def create(self, user: AuthenticatedUser) -> str:
        session_id = secrets.token_urlsafe(32)
        await self._redis.set(self._key(session_id), _user_to_json(user), ex=_TTL_SECONDS)
        return session_id

    async def get(self, session_id: str) -> AuthenticatedUser | None:
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            return None
        return _user_from_json(raw)

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(self._key(session_id))
