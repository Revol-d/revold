"""Monta a implementação de OrderRepository contra o Azure SQL Database. Mesmo
padrão de revold_store_settings.adapters.factory. Postgres foi removido (Fase 7 do
plano de migração Postgres -> Azure SQL, docs internos).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_orders.adapters.azure_sql.repository import AzureSqlOrderRepository
from revold_orders.ports import OrderRepository


def build_order_repository(session: AsyncSession) -> OrderRepository:
    return AzureSqlOrderRepository(session)
