"""Teste de contrato do router de identity: sobe o app FastAPI de verdade,
com o provider e o repositório de sessão trocados por fakes em memória."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_api_key_auth, get_identity_provider, get_session_repository
from api_gateway.main import app
from api_gateway.security import get_current_user
from revold_identity.domain import ApiKeyNotFound, ApiKeyPrincipal, AuthenticatedUser, Role


class _FakeIdentityProvider:
    """Mesma forma do DevIdentityProvider, mas sem estado global."""

    provider_name = "fake"

    def start_login(self, *, redirect_uri: str):
        from revold_identity.domain import LoginChallenge

        return LoginChallenge(authorize_url=f"{redirect_uri}?code=fake&state=fake", state="fake")

    async def complete_login(self, *, code: str, state: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            external_id="ext-1",
            provider=self.provider_name,
            email="nick@example.com",
            name="Nick",
            roles=(Role.CUSTOMER, Role.ADMIN),
        )


class _FakeSessionRepository:
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


class _FakeApiKeyAuth:
    """Mesma forma da FakeApiKeyAuth de libs/domains/identity/tests/conftest.py
    — duplicada aqui de propósito (convenção deste monorepo: cada suíte
    mantém seus próprios fakes, ver docstring de outros testes)."""

    def __init__(self) -> None:
        self._by_raw_key: dict[str, ApiKeyPrincipal] = {}
        self._principals: dict[str, ApiKeyPrincipal] = {}

    async def issue(self, *, name: str) -> tuple[ApiKeyPrincipal, str]:
        import secrets
        import uuid

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


_ADMIN_USER = AuthenticatedUser(
    external_id="admin-1", provider="dev", email="admin@example.com", name="Admin",
    roles=(Role.ADMIN,),
)
_STAFF_USER = AuthenticatedUser(
    external_id="staff-1", provider="dev", email="staff@example.com", name="Staff",
    roles=(Role.STAFF,),
)


@pytest.fixture(autouse=True)
def override_api_key_auth():
    fake_auth = _FakeApiKeyAuth()
    app.dependency_overrides[get_api_key_auth] = lambda: fake_auth
    yield fake_auth
    app.dependency_overrides.pop(get_api_key_auth, None)


@pytest.fixture(autouse=True)
def override_dependencies():
    # Uma única instância por teste: o fake precisa persistir sessões entre
    # requisições (login/complete cria, /me lê), então a mesma instância tem
    # que ser devolvida a cada resolução da dependência.
    fake_provider = _FakeIdentityProvider()
    fake_sessions = _FakeSessionRepository()
    app.dependency_overrides[get_identity_provider] = lambda: fake_provider
    app.dependency_overrides[get_session_repository] = lambda: fake_sessions
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_login_start_retorna_challenge(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login/start", json={"redirect_uri": "http://localhost:3000/callback"}
    )
    assert response.status_code == 200
    assert response.json()["state"] == "fake"


async def test_login_complete_seta_cookie_e_retorna_usuario(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login/complete", json={"code": "fake", "state": "fake"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "nick@example.com"
    assert body["roles"] == ["customer", "admin"]
    assert "session_id" in response.cookies


async def test_me_sem_cookie_retorna_401(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_me_com_cookie_valido_retorna_usuario(client: AsyncClient) -> None:
    login_response = await client.post(
        "/api/auth/login/complete", json={"code": "fake", "state": "fake"}
    )
    session_id = login_response.cookies["session_id"]

    response = await client.get("/api/auth/me", cookies={"session_id": session_id})
    assert response.status_code == 200
    assert response.json()["email"] == "nick@example.com"


async def test_me_com_cookie_invalido_retorna_401(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me", cookies={"session_id": "nao-existe"})
    assert response.status_code == 401


async def test_logout_apaga_sessao(client: AsyncClient) -> None:
    login_response = await client.post(
        "/api/auth/login/complete", json={"code": "fake", "state": "fake"}
    )
    session_id = login_response.cookies["session_id"]

    logout_response = await client.post("/api/auth/logout", cookies={"session_id": session_id})
    assert logout_response.status_code == 204

    me_response = await client.get("/api/auth/me", cookies={"session_id": session_id})
    assert me_response.status_code == 401


async def test_issue_api_key_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post("/api/auth/api-keys", json={"name": "Parceiro ERP"})
    assert response.status_code == 401


async def test_issue_api_key_com_papel_staff_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post("/api/auth/api-keys", json={"name": "Parceiro ERP"})
    assert response.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


async def test_issue_api_key_com_papel_admin_emite_chave(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER
    response = await client.post("/api/auth/api-keys", json={"name": "Parceiro ERP"})
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Parceiro ERP"
    assert body["key_id"]
    assert body["raw_key"]


async def test_revoke_api_key_com_papel_admin_revoga(
    client: AsyncClient, override_api_key_auth: _FakeApiKeyAuth
) -> None:
    principal, _raw_key = await override_api_key_auth.issue(name="Parceiro ERP")

    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER
    response = await client.delete(f"/api/auth/api-keys/{principal.key_id}")
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 204


async def test_revoke_api_key_inexistente_retorna_404(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _ADMIN_USER
    response = await client.delete("/api/auth/api-keys/nao-existe")
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


async def test_revoke_api_key_com_papel_staff_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.delete("/api/auth/api-keys/qualquer-um")
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
