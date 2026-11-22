"""Monta a implementação de InventoryRepository contra o Azure SQL Database. Mesmo
padrão de revold_store_settings.adapters.factory. Postgres foi removido (Fase 7 do
plano de migração Postgres -> Azure SQL, docs internos).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_inventory.adapters.azure_sql.repository import AzureSqlInventoryRepository
from revold_inventory.ports import InventoryRepository


def build_inventory_repository(session: AsyncSession) -> InventoryRepository:
    return AzureSqlInventoryRepository(session)
