"""Monta a implementação de StoreSettingsRepository contra o Azure SQL Database.

A `session` (SQLAlchemy async, já ligada ao engine do Azure SQL) vem pronta de
`dependencies.py` -- aqui só se embrulha essa sessão no repository. Postgres foi
removido (Fase 7 do plano de migração Postgres -> Azure SQL, docs internos):
troca única, não suporte dual permanente.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_store_settings.adapters.azure_sql.repository import AzureSqlStoreSettingsRepository
from revold_store_settings.ports import StoreSettingsRepository


def build_store_settings_repository(session: AsyncSession) -> StoreSettingsRepository:
    return AzureSqlStoreSettingsRepository(session)
