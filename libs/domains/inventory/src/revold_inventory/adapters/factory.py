"""Seleciona a implementação de InventoryRepository pelo nome do provedor de
persistência. Mesmo padrão de revold_store_settings.adapters.factory -- ver lá para o
porquê deste factory não ler o ambiente nem montar a sessão.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_inventory.ports import InventoryRepository

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_inventory_repository(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> InventoryRepository:
    if provider == "postgres":
        from revold_inventory.adapters.postgres.repository import PostgresInventoryRepository

        return PostgresInventoryRepository(session)
    if provider == "azure-sql":
        from revold_inventory.adapters.azure_sql.repository import AzureSqlInventoryRepository

        return AzureSqlInventoryRepository(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
