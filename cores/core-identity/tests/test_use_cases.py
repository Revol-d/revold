from __future__ import annotations

import pytest

from adapters_external.identity.dev_provider import DevIdentityProvider
from core_identity.domain import ApiKeyNotFound
from core_identity.use_cases import (
    CompleteLogin,
    GetCurrentUser,
    IssueApiKey,
    Logout,
    RevokeApiKey,
    StartLogin,
)


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


async def test_issue_api_key_devolve_principal_e_chave_em_texto_puro(
    fake_api_key_auth,
) -> None:
    principal, raw_key = await IssueApiKey(fake_api_key_auth).execute(name="Parceiro ERP")
    assert principal.name == "Parceiro ERP"
    assert principal.key_id
    assert raw_key

    resolved = await fake_api_key_auth.resolve(raw_key)
    assert resolved == principal


async def test_revoke_api_key_impede_resolucao_futura(fake_api_key_auth) -> None:
    principal, raw_key = await IssueApiKey(fake_api_key_auth).execute(name="Parceiro ERP")

    await RevokeApiKey(fake_api_key_auth).execute(principal.key_id)

    assert await fake_api_key_auth.resolve(raw_key) is None


async def test_revoke_api_key_inexistente_levanta_erro(fake_api_key_auth) -> None:
    with pytest.raises(ApiKeyNotFound):
        await RevokeApiKey(fake_api_key_auth).execute("nao-existe")
