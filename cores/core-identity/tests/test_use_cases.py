from __future__ import annotations

from adapters_external.identity.dev_provider import DevIdentityProvider
from core_identity.use_cases import CompleteLogin, GetCurrentUser, Logout, StartLogin


def test_start_login_delega_para_o_provider() -> None:
    challenge = StartLogin(DevIdentityProvider()).execute(
        redirect_uri="http://localhost:3000/callback"
    )
    assert challenge.state == "dev"


async def test_complete_login_cria_sessao(fake_sessions) -> None:
    session_id, user = await CompleteLogin(DevIdentityProvider(), fake_sessions).execute(
        code="dev", state="dev"
    )
    assert session_id
    assert user.provider == "dev"
    stored = await fake_sessions.get(session_id)
    assert stored == user


async def test_get_current_user_retorna_none_para_sessao_inexistente(fake_sessions) -> None:
    user = await GetCurrentUser(fake_sessions).execute("nao-existe")
    assert user is None


async def test_get_current_user_retorna_usuario_da_sessao(fake_sessions) -> None:
    session_id, user = await CompleteLogin(DevIdentityProvider(), fake_sessions).execute(
        code="dev", state="dev"
    )
    found = await GetCurrentUser(fake_sessions).execute(session_id)
    assert found == user


async def test_logout_apaga_a_sessao(fake_sessions) -> None:
    session_id, _ = await CompleteLogin(DevIdentityProvider(), fake_sessions).execute(
        code="dev", state="dev"
    )
    await Logout(fake_sessions).execute(session_id)
    assert await fake_sessions.get(session_id) is None
