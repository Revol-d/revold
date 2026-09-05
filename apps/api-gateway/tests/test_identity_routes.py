"""Teste de contrato do router de identity: sobe o app FastAPI de verdade,
com o provider e o repositório de sessão trocados por fakes em memória."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import get_identity_provider, get_session_repository
from api_gateway.main import app
from core_identity.domain import AuthenticatedUser, Role


class _FakeIdentityProvider:
    """Mesma forma do DevIdentityProvider, mas sem estado global."""

    provider_name = "fake"

    def start_login(self, *, redirect_uri: str):
        from core_identity.domain import LoginChallenge

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
