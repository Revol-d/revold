"""Adapter de desenvolvimento do IdentityProvider (ADR-0003).

Não fala com nenhum serviço externo: "loga" instantaneamente como um usuário
fixo, para permitir desenvolver e testar todo o resto do sistema (carrinho,
checkout, admin) sem depender de app registration real no Azure AD/Google.
Nunca deve ser usado fora de ambiente de desenvolvimento — ver factory.py,
que só o seleciona quando AUTH_PROVIDER=dev (o padrão do .env.example).
"""
from __future__ import annotations

import uuid

from revold_identity.domain import AuthenticatedUser, LoginChallenge, Role


class DevIdentityProvider:
    provider_name = "dev"

    def start_login(self, *, redirect_uri: str) -> LoginChallenge:
        # Não existe redirecionamento real: o "state" só marca a intenção de
        # login para o frontend seguir o mesmo fluxo de callback dos
        # provedores reais.
        return LoginChallenge(authorize_url=f"{redirect_uri}?code=dev&state=dev", state="dev")

    async def complete_login(self, *, code: str, state: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            external_id=f"dev-{uuid.uuid4()}",
            provider=self.provider_name,
            email="dev@example.com",
            name="Usuário de Desenvolvimento",
            roles=(Role.CUSTOMER, Role.ADMIN),
        )
