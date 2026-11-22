"""Monta a implementação de ProductRepository contra o Azure SQL Database. Mesmo
padrão de revold_store_settings.adapters.factory. Postgres foi removido (Fase 7 do
plano de migração Postgres -> Azure SQL, docs internos).

Não confundir com revold_catalog.adapters.media.factory.build_media_storage
(local/azure-blob via MEDIA_STORAGE_PROVIDER) -- porta e fábrica diferentes do
mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_catalog.adapters.azure_sql.repository import AzureSqlProductRepository
from revold_catalog.ports import ProductRepository


def build_product_repository(session: AsyncSession) -> ProductRepository:
    return AzureSqlProductRepository(session)
