"""Seleciona a implementação de ProductRepository pelo nome do provedor de
persistência. Mesmo padrão de revold_store_settings.adapters.factory.

Não confundir com revold_catalog.adapters.media.factory.build_media_storage
(local/azure-blob via MEDIA_STORAGE_PROVIDER) -- porta e fábrica diferentes do
mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_catalog.ports import ProductRepository

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_product_repository(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> ProductRepository:
    if provider == "postgres":
        from revold_catalog.adapters.postgres.repository import PostgresProductRepository

        return PostgresProductRepository(session)
    if provider == "azure-sql":
        from revold_catalog.adapters.azure_sql.repository import AzureSqlProductRepository

        return AzureSqlProductRepository(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
