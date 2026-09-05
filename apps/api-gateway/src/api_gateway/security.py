"""Dependências de autenticação/autorização do api-gateway (ADR-0010).

Vivem aqui, e não em core_identity, porque dependem de FastAPI (Request,
HTTPException, cookies) — um core nunca pode depender de FastAPI (ADR-0002).
A sessão em si (criação/leitura/expiração) continua sendo responsabilidade
do core, via o caso de uso GetCurrentUser; este módulo só traduz
cookie HTTP <-> chamada ao core e transforma "sem usuário" em HTTP 401/403.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from api_gateway.dependencies import get_session_repository
from core_identity.domain import AuthenticatedUser, Role
from core_identity.ports import SessionRepository
from core_identity.use_cases import GetCurrentUser

SESSION_COOKIE_NAME = "session_id"


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
