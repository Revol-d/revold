"""Porta que todo provedor de identidade (real ou de desenvolvimento) implementa.

Ver ADR-0003: nenhuma implementação desta porta guarda senha. O que muda entre
um provedor e outro é só para onde o login redireciona e como o callback é
validado — a interface é sempre a mesma, para que trocar de provedor seja
configuração (AUTH_PROVIDER), não mudança de código no core nem no storefront.
"""
from __future__ import annotations

from typing import Protocol

from core_identity.domain import AuthenticatedUser, LoginChallenge


class IdentityProvider(Protocol):
    provider_name: str

    def start_login(self, *, redirect_uri: str) -> LoginChallenge:
        """Gera a URL de autorização para redirecionar o usuário."""
        ...

    async def complete_login(self, *, code: str, state: str) -> AuthenticatedUser:
        """Troca o código de autorização pela identidade autenticada."""
        ...
