"""Dependências de autenticação/autorização do api-gateway (ADR-0010).

Vivem aqui, e não em core_identity, porque dependem de FastAPI (Request,
HTTPException, cookies) — um core nunca pode depender de FastAPI (ADR-0002).
A sessão em si (criação/leitura/expiração) continua sendo responsabilidade
do core, via o caso de uso GetCurrentUser; este módulo só traduz
cookie HTTP <-> chamada ao core e transforma "sem usuário" em HTTP 401/403.
"""
from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request

from api_gateway.dependencies import get_api_key_auth, get_rate_limiter, get_session_repository
from core_identity.domain import ApiKeyPrincipal, AuthenticatedUser, Role
from core_identity.ports import ApiKeyAuth, RateLimiter, SessionRepository
from core_identity.use_cases import GetCurrentUser

SESSION_COOKIE_NAME = "session_id"
API_KEY_HEADER_NAME = "X-API-Key"


async def get_current_user(
    request: Request,
    sessions: SessionRepository = Depends(get_session_repository),
) -> AuthenticatedUser:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is None:
        raise HTTPException(status_code=401, detail="Não autenticado")

    user = await GetCurrentUser(sessions).execute(session_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")

    return user


def require_any_role(*roles: Role):
    """Fábrica de dependência: exige que o usuário autenticado tenha ao
    menos um dos papéis informados, senão 403.

    Uso: `Depends(require_any_role(Role.STAFF, Role.ADMIN))`.
    """

    async def _dependency(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not any(user.has_role(role) for role in roles):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return user

    return _dependency


def _default_rate_limit() -> int:
    return int(os.environ.get("PUBLIC_API_RATE_LIMIT", "60"))


def _default_rate_limit_window_seconds() -> int:
    return int(os.environ.get("PUBLIC_API_RATE_LIMIT_WINDOW_SECONDS", "60"))


async def require_api_key_principal(
    request: Request,
    api_key_auth: ApiKeyAuth = Depends(get_api_key_auth),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> ApiKeyPrincipal:
    """Autentica um chamador externo (parceiro/integração) via header
    X-API-Key e aplica rate limit por chave (ADR-0016) — nunca envolve
    sessão de navegador nem cookie, é a porta de entrada para a API
    pública/parceiro, separada da autenticação por sessão usada pelo
    storefront/admin-dashboard."""
    raw_key = request.headers.get(API_KEY_HEADER_NAME)
    if raw_key is None:
        raise HTTPException(status_code=401, detail=f"Header {API_KEY_HEADER_NAME} ausente")

    principal = await api_key_auth.resolve(raw_key)
    if principal is None:
        raise HTTPException(status_code=401, detail="API key inválida ou revogada")

    allowed = await rate_limiter.allow(
        principal.key_id,
        limit=_default_rate_limit(),
        window_seconds=_default_rate_limit_window_seconds(),
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Limite de requisições excedido")

    return principal
