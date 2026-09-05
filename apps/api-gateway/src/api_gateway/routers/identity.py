"""Router HTTP do core-identity (ADR-0003, ADR-0010).

Login é sempre federado (nunca há senha local, ver ADR-0003): o frontend
pede a URL de autorização em /login/start, redireciona o usuário ao
provedor, e troca code+state pelo usuário autenticado em /login/complete
— que abre uma sessão e devolve o id dela num cookie HttpOnly (ADR-0010).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request, Response

from api_gateway.dependencies import get_identity_provider, get_session_repository
from api_gateway.security import SESSION_COOKIE_NAME, get_current_user
from core_identity.domain import AuthenticatedUser
from core_identity.ports import IdentityProvider, SessionRepository
from core_identity.schemas import (
    AuthenticatedUserSchema,
    CompleteLoginRequestSchema,
    LoginChallengeSchema,
    StartLoginRequestSchema,
)
from core_identity.use_cases import CompleteLogin, Logout, StartLogin

router = APIRouter(prefix="/api/auth", tags=["identity"])

# Mesmo TTL usado pelo RedisSessionRepository (ver ADR-0010) — o cookie não
# deve sobreviver além da sessão no Redis.
_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def _cookie_secure() -> bool:
    # Em dev local (sem HTTPS) o cookie Secure nunca seria enviado pelo
    # navegador; SESSION_COOKIE_SECURE=false destrava isso só localmente.
    return os.environ.get("SESSION_COOKIE_SECURE", "true").lower() != "false"


def _user_to_schema(user: AuthenticatedUser) -> AuthenticatedUserSchema:
    return AuthenticatedUserSchema(
        external_id=user.external_id,
        provider=user.provider,
        email=user.email,
        name=user.name,
        roles=[role.value for role in user.roles],
    )


@router.post("/login/start", response_model=LoginChallengeSchema)
async def start_login(
    body: StartLoginRequestSchema,
    provider: IdentityProvider = Depends(get_identity_provider),
) -> LoginChallengeSchema:
    challenge = StartLogin(provider).execute(redirect_uri=body.redirect_uri)
    return LoginChallengeSchema(authorize_url=challenge.authorize_url, state=challenge.state)


@router.post("/login/complete", response_model=AuthenticatedUserSchema)
async def complete_login(
    body: CompleteLoginRequestSchema,
    response: Response,
    provider: IdentityProvider = Depends(get_identity_provider),
    sessions: SessionRepository = Depends(get_session_repository),
) -> AuthenticatedUserSchema:
    session_id, user = await CompleteLogin(provider, sessions).execute(
        code=body.code, state=body.state
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
    )
    return _user_to_schema(user)


@router.post("/logout", status_code=204, response_model=None)
async def logout(
    request: Request,
    response: Response,
    sessions: SessionRepository = Depends(get_session_repository),
) -> None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id is not None:
        await Logout(sessions).execute(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=AuthenticatedUserSchema)
async def get_me(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUserSchema:
    return _user_to_schema(user)
