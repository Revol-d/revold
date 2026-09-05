from __future__ import annotations

import pytest

from core_identity.domain import AuthenticatedUser


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
