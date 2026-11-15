"""Router HTTP do `identity` (ADR-0003, ADR-0010).

Login é sempre federado (nunca há senha local, ver ADR-0003): o frontend
pede a URL de autorização em /login/start, redireciona o usuário ao
provedor, e troca code+state pelo usuário autenticado em /login/complete
— que abre uma sessão e devolve o id dela num cookie HttpOnly (ADR-0010).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api_gateway.dependencies import get_api_key_auth, get_identity_provider, get_session_repository
from api_gateway.security import SESSION_COOKIE_NAME, get_current_user, require_any_role
from api_gateway.settings import session_cookie_secure
from revold_identity.domain import ApiKeyNotFound, AuthenticatedUser, Role
from revold_identity.ports import ApiKeyAuth, IdentityProvider, SessionRepository
from revold_identity.application.schemas import (
    AuthenticatedUserSchema,
    CompleteLoginRequestSchema,
    IssueApiKeyRequestSchema,
    IssuedApiKeySchema,
    LoginChallengeSchema,
    StartLoginRequestSchema,
)
from revold_identity.application.use_cases import CompleteLogin, IssueApiKey, Logout, RevokeApiKey, StartLogin

router = APIRouter(prefix="/api/auth", tags=["identity"])

# Mesmo TTL usado pelo RedisSessionRepository (ver ADR-0010) — o cookie não
# deve sobreviver além da sessão no Redis.
_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def _cookie_secure() -> bool:
    # Em dev local (sem HTTPS) o cookie Secure nunca seria enviado pelo
    # navegador; SESSION_COOKIE_SECURE=false destrava isso só localmente.
    return session_cookie_secure()


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


@router.post("/api-keys", response_model=IssuedApiKeySchema, status_code=201)
async def issue_api_key(
    body: IssueApiKeyRequestSchema,
    api_key_auth: ApiKeyAuth = Depends(get_api_key_auth),
    _admin: AuthenticatedUser = Depends(require_any_role(Role.ADMIN)),
) -> IssuedApiKeySchema:
    """Emite uma API key para um parceiro/integração (ADR-0016) — só ADMIN,
    diferente dos endpoints administrativos de catálogo/estoque (que também
    aceitam STAFF): dar acesso de API pública é mais sensível que editar
    produto. `raw_key` só existe nesta resposta — perdida a partir daqui."""
    principal, raw_key = await IssueApiKey(api_key_auth).execute(name=body.name)
    return IssuedApiKeySchema(key_id=principal.key_id, name=principal.name, raw_key=raw_key)


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    api_key_auth: ApiKeyAuth = Depends(get_api_key_auth),
    _admin: AuthenticatedUser = Depends(require_any_role(Role.ADMIN)),
) -> Response:
    try:
        await RevokeApiKey(api_key_auth).execute(key_id)
    except ApiKeyNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)
