"""Fábricas de dados (Factory Boy + Faker, locale pt_BR) para
`core_identity.domain`.

`AuthenticatedUser`/`ApiKeyPrincipal` não têm validação de domínio hoje
(`__post_init__` nenhum) — a fábrica aqui não existe pra pegar bug de
validação (não há nenhuma), mas pra parar de repetir
`AuthenticatedUser(external_id="u1", provider="dev", email="a@a.com",
name="Fulano")` em todo teste que só precisa "de um usuário autenticado
qualquer" (ex. testes de RBAC em `apps/api-gateway/tests/`), com e-mail e
nome plausíveis (pt_BR) em vez de sempre o mesmo placeholder.
"""
from __future__ import annotations

import factory
from faker import Faker

from core_identity.domain import ApiKeyPrincipal, AuthenticatedUser, Role

fake = Faker("pt_BR")


class AuthenticatedUserFactory(factory.Factory):
    class Meta:
        model = AuthenticatedUser

    external_id = factory.LazyFunction(lambda: fake.unique.uuid4())
    provider = "dev"
    email = factory.LazyFunction(lambda: fake.unique.email())
    name = factory.LazyFunction(fake.name)
    roles = (Role.CUSTOMER,)


class ApiKeyPrincipalFactory(factory.Factory):
    class Meta:
        model = ApiKeyPrincipal

    key_id = factory.LazyFunction(lambda: fake.unique.uuid4())
    name = factory.LazyFunction(lambda: f"Integração {fake.company()}")
