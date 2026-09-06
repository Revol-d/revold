"""Casos de uso do core-identity."""
from __future__ import annotations

from core_identity.domain import ApiKeyPrincipal, AuthenticatedUser, LoginChallenge
from core_identity.ports import ApiKeyAuth, IdentityProvider, SessionRepository


class StartLogin:
    def __init__(self, provider: IdentityProvider) -> None:
        self._provider = provider

    def execute(self, *, redirect_uri: str) -> LoginChallenge:
        return self._provider.start_login(redirect_uri=redirect_uri)


class CompleteLogin:
    """Troca o código de autorização por uma identidade autenticada e abre
    uma sessão (ADR-0010) — devolve o session_id que o api-gateway coloca
    no cookie HttpOnly, nunca no corpo da resposta."""

    def __init__(self, provider: IdentityProvider, sessions: SessionRepository) -> None:
        self._provider = provider
        self._sessions = sessions

    async def execute(self, *, code: str, state: str) -> tuple[str, AuthenticatedUser]:
        user = await self._provider.complete_login(code=code, state=state)
        session_id = await self._sessions.create(user)
        return session_id, user


class GetCurrentUser:
    def __init__(self, sessions: SessionRepository) -> None:
        self._sessions = sessions

    async def execute(self, session_id: str) -> AuthenticatedUser | None:
        return await self._sessions.get(session_id)


class Logout:
    def __init__(self, sessions: SessionRepository) -> None:
        self._sessions = sessions

    async def execute(self, session_id: str) -> None:
        await self._sessions.delete(session_id)


class IssueApiKey:
    """Emite uma API key nova para um parceiro/integração (ADR-0016) — uso
    administrativo (RBAC ADMIN aplicado no api-gateway). A chave em texto
    puro só existe no retorno desta chamada; perdida a partir daí."""

    def __init__(self, auth: ApiKeyAuth) -> None:
        self._auth = auth

    async def execute(self, *, name: str) -> tuple[ApiKeyPrincipal, str]:
        return await self._auth.issue(name=name)


class RevokeApiKey:
    """Revoga uma API key existente — uso administrativo (RBAC ADMIN
    aplicado no api-gateway). Levanta ApiKeyNotFound se key_id não existir
    (ver core_identity.domain)."""

    def __init__(self, auth: ApiKeyAuth) -> None:
        self._auth = auth

    async def execute(self, key_id: str) -> None:
        await self._auth.revoke(key_id)
