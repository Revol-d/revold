"""Monta a implementação de ApiKeyAuth contra o Azure SQL Database. Mesmo padrão de
revold_store_settings.adapters.factory. Postgres foi removido (Fase 7 do plano de
migração Postgres -> Azure SQL, docs internos).

Não confundir com revold_identity.adapters.providers.factory.build_identity_provider
(dev/azure-ad/google via AUTH_PROVIDER) nem com os adapters Redis de
SessionRepository/RateLimiter -- são portas e fábricas independentes do mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_identity.adapters.azure_sql.api_key_auth import AzureSqlApiKeyAuth
from revold_identity.ports import ApiKeyAuth


def build_api_key_auth(session: AsyncSession) -> ApiKeyAuth:
    return AzureSqlApiKeyAuth(session)
