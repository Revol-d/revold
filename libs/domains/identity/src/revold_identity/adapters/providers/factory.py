"""Seleciona a implementação de IdentityProvider pelo nome do provedor.

Este é o único lugar que decide qual adapter usar — trocar de provedor em
produção é mudar a configuração, nunca importar um adapter diferente
manualmente em outro módulo.

Este módulo não lê o ambiente. O nome vem do `settings.py` do app (variável
`AUTH_PROVIDER`).
"""
from __future__ import annotations

from revold_identity.adapters.providers.dev_provider import DevIdentityProvider
from revold_identity.ports import IdentityProvider

DEFAULT_AUTH_PROVIDER = "dev"


def build_identity_provider(provider: str = DEFAULT_AUTH_PROVIDER) -> IdentityProvider:
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
