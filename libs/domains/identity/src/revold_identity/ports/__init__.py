"""Porta que todo provedor de identidade (real ou de desenvolvimento) implementa.

Ver ADR-0003: nenhuma implementação desta porta guarda senha. O que muda entre
um provedor e outro é só para onde o login redireciona e como o callback é
validado — a interface é sempre a mesma, para que trocar de provedor seja
configuração (AUTH_PROVIDER), não mudança de código no core nem no storefront.
"""
from __future__ import annotations

from typing import Protocol

from revold_identity.domain import ApiKeyPrincipal, AuthenticatedUser, LoginChallenge


class IdentityProvider(Protocol):
    provider_name: str

    def start_login(self, *, redirect_uri: str) -> LoginChallenge:
        """Gera a URL de autorização para redirecionar o usuário."""
        ...

    async def complete_login(self, *, code: str, state: str) -> AuthenticatedUser:
        """Troca o código de autorização pela identidade autenticada."""
        ...


class SessionRepository(Protocol):
    """Porta de sessão (ADR-0010). O cookie do navegador carrega só o id
    opaco devolvido por `create` — nenhum dado de usuário nem claim viaja
    para o cliente."""

    async def create(self, user: AuthenticatedUser) -> str:
        """Cria uma sessão para o usuário e devolve o session_id opaco."""
        ...

    async def get(self, session_id: str) -> AuthenticatedUser | None: ...

    async def delete(self, session_id: str) -> None: ...


class ApiKeyAuth(Protocol):
    """Porta de autenticação para chamadores externos (parceiro/integração)
    da API pública — nunca envolve senha nem sessão de navegador (ADR-0016).

    `issue` é o único momento em que a chave em texto puro existe: quem
    implementa guarda só o hash, e devolve a chave puro uma única vez para
    quem chamou — perdida a partir daí, só dá pra revogar e emitir outra."""

    async def issue(self, *, name: str) -> tuple[ApiKeyPrincipal, str]:
        """Gera uma chave nova, guarda seu hash, devolve (principal, chave_em_texto_puro)."""
        ...

    async def resolve(self, raw_key: str) -> ApiKeyPrincipal | None:
        """Resolve uma chave em texto puro (ex. vinda do header X-API-Key)
        para o principal dono dela, ou None se inválida/revogada."""
        ...

    async def revoke(self, key_id: str) -> None:
        """Levanta ApiKeyNotFound se key_id não existir."""
        ...


class RateLimiter(Protocol):
    """Token bucket de janela fixa (ADR-0016) — protege a API pública de
    abuso por parceiro/integração. `principal_id` é o que particiona os
    buckets: cada chamador tem o seu, independente dos demais."""

    async def allow(self, principal_id: str, *, limit: int, window_seconds: int) -> bool:
        """True se esta chamada está dentro do limite (e conta para ele);
        False se o limite já foi atingido nesta janela."""
        ...
