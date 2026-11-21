"""Seleciona a implementação de OrderRepository pelo nome do provedor de
persistência. Mesmo padrão de revold_store_settings.adapters.factory.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_orders.ports import OrderRepository

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_order_repository(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> OrderRepository:
    if provider == "postgres":
        from revold_orders.adapters.postgres.repository import PostgresOrderRepository

        return PostgresOrderRepository(session)
    if provider == "azure-sql":
        from revold_orders.adapters.azure_sql.repository import AzureSqlOrderRepository

        return AzureSqlOrderRepository(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
