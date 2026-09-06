from __future__ import annotations

import secrets
import uuid

import pytest

from core_identity.domain import ApiKeyNotFound, ApiKeyPrincipal, AuthenticatedUser


class FakeApiKeyAuth:
    """Adapter fake em memória, mesma forma da porta ApiKeyAuth, só para
    teste — guarda a chave em texto puro só para o teste poder resolvê-la
    de volta (um adapter real nunca faria isso, ver PostgresApiKeyAuth)."""

    def __init__(self) -> None:
        self._by_raw_key: dict[str, ApiKeyPrincipal] = {}
        self._principals: dict[str, ApiKeyPrincipal] = {}

    async def issue(self, *, name: str) -> tuple[ApiKeyPrincipal, str]:
        principal = ApiKeyPrincipal(key_id=str(uuid.uuid4()), name=name)
        raw_key = f"fake_{secrets.token_hex(8)}"
        self._by_raw_key[raw_key] = principal
        self._principals[principal.key_id] = principal
        return principal, raw_key

    async def resolve(self, raw_key: str) -> ApiKeyPrincipal | None:
        principal = self._by_raw_key.get(raw_key)
        if principal is None or principal.key_id not in self._principals:
            return None
        return principal

    async def revoke(self, key_id: str) -> None:
        if key_id not in self._principals:
            raise ApiKeyNotFound(key_id)
        del self._principals[key_id]


@pytest.fixture
def fake_api_key_auth() -> FakeApiKeyAuth:
    return FakeApiKeyAuth()


class FakeSessionRepository:
    """Adapter fake em memória, mesma forma da porta SessionRepository, só para teste."""

    def __init__(self) -> None:
        self._sessions: dict[str, AuthenticatedUser] = {}
        self._next_id = 0

    async def create(self, user: AuthenticatedUser) -> str:
        self._next_id += 1
        session_id = f"fake-session-{self._next_id}"
        self._sessions[session_id] = user
        return session_id

    async def get(self, session_id: str) -> AuthenticatedUser | None:
        return self._sessions.get(session_id)

    async def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


@pytest.fixture
def fake_sessions() -> FakeSessionRepository:
    return FakeSessionRepository()
