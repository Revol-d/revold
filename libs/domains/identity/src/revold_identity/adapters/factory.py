"""Seleciona a implementação de ApiKeyAuth pelo nome do provedor de persistência.
Mesmo padrão de revold_store_settings.adapters.factory.

Não confundir com revold_identity.adapters.providers.factory.build_identity_provider
(dev/azure-ad/google via AUTH_PROVIDER) nem com os adapters Redis de
SessionRepository/RateLimiter -- são portas e fábricas independentes do mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_identity.ports import ApiKeyAuth

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_api_key_auth(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> ApiKeyAuth:
    if provider == "postgres":
        from revold_identity.adapters.postgres.api_key_auth import PostgresApiKeyAuth

        return PostgresApiKeyAuth(session)
    if provider == "azure-sql":
        from revold_identity.adapters.azure_sql.api_key_auth import AzureSqlApiKeyAuth

        return AzureSqlApiKeyAuth(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
