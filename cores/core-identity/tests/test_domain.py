"""Testes diretos dos objetos de domínio de `core_identity`.

`AuthenticatedUser`/`ApiKeyPrincipal` não têm nenhuma validação em
`__post_init__` hoje — não há regra de negócio pra "pegar" aqui. O valor
destes testes é outro: confirmar que a fábrica (`revold_testing.identity_factories`,
usada por qualquer teste do resto do monorepo que só precisa "de um
usuário autenticado qualquer") gera dado plausível e sem colisão, em vez
de todo teste repetir o mesmo `AuthenticatedUser(external_id="u1", ...)`
com e-mail placeholder.
"""
from __future__ import annotations

from revold_testing.identity_factories import ApiKeyPrincipalFactory, AuthenticatedUserFactory

from core_identity.domain import Role


def test_fabrica_gera_usuario_com_role_customer_por_padrao() -> None:
    user = AuthenticatedUserFactory()
    assert user.has_role(Role.CUSTOMER)
    assert not user.has_role(Role.ADMIN)
    assert "@" in user.email


def test_fabrica_permite_sobrescrever_roles() -> None:
    admin = AuthenticatedUserFactory(roles=(Role.ADMIN, Role.STAFF))
    assert admin.has_role(Role.ADMIN)
    assert admin.has_role(Role.STAFF)
    assert not admin.has_role(Role.CUSTOMER)


def test_fabrica_gera_external_ids_e_emails_distintos_entre_usuarios() -> None:
    # Regressão contra dois testes que criam usuários "genéricos" na mesma
    # sessão de pytest acabarem com o mesmo external_id/email por acidente
    # (ver `fake.unique` em revold_testing.identity_factories).
    a, b = AuthenticatedUserFactory(), AuthenticatedUserFactory()
    assert a.external_id != b.external_id
    assert a.email != b.email


def test_fabrica_de_api_key_principal_gera_nome_de_integracao_plausivel() -> None:
    principal = ApiKeyPrincipalFactory()
    assert principal.key_id
    assert principal.name.startswith("Integração ")
