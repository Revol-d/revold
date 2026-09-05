"""Seleciona a implementação de IdentityProvider a partir de AUTH_PROVIDER.

Este é o único lugar que decide qual adapter usar — trocar de provedor em
produção é mudar a variável de ambiente, nunca importar um adapter
diferente manualmente em outro módulo.
"""
from __future__ import annotations

import os

from core_identity.ports import IdentityProvider

from adapters_external.identity.dev_provider import DevIdentityProvider


def get_identity_provider() -> IdentityProvider:
    provider = os.environ.get("AUTH_PROVIDER", "dev")
    if provider == "dev":
        return DevIdentityProvider()
    if provider == "azure-ad":
        raise NotImplementedError(
            "Adapter do Azure AD B2C/Entra External ID (MSAL) ainda não implementado. "
            "Requer AZURE_AD_TENANT_ID/CLIENT_ID/CLIENT_SECRET reais (ver ADR-0003 e .env.example) "
            "para poder ser desenvolvido e testado contra o tenant de verdade."
        )
    if provider == "google":
        raise NotImplementedError(
            "Adapter do Google (OAuth2/OIDC) ainda não implementado. "
            "Requer GOOGLE_CLIENT_ID/CLIENT_SECRET reais (ver .env.example)."
        )
    raise ValueError(f"AUTH_PROVIDER desconhecido: {provider!r}")
