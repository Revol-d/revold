"""Ponto de entrada de `python -m api_gateway.seed` (ver `make seed`, ADR-0022).

Só monta as dependências reais (Azure SQL) e chama os casos de uso de
`revold_ecommerce.application.seed`, que é onde a regra do seed mora. Roda no container do
api-gateway porque é ele que já tem o banco e os repositórios configurados.
"""

from __future__ import annotations

import asyncio

from api_gateway.settings import database_url
from revold_azure_sql.db import make_engine, make_session_factory
from revold_catalog.adapters.azure_sql.repository import AzureSqlProductRepository
from revold_ecommerce.application.seed import format_seed_report, seed_catalog, seed_store_settings
from revold_inventory.adapters.azure_sql.repository import AzureSqlInventoryRepository
from revold_store_settings.adapters.azure_sql.repository import AzureSqlStoreSettingsRepository


async def run_seed() -> None:
    engine = make_engine(database_url())
    session_factory = make_session_factory(engine)
    try:
        async with session_factory() as session:
            catalog = await seed_catalog(
                AzureSqlProductRepository(session), AzureSqlInventoryRepository(session)
            )
            settings_created = await seed_store_settings(AzureSqlStoreSettingsRepository(session))
    finally:
        await engine.dispose()

    for line in format_seed_report(catalog, settings_created=settings_created):
        print(line)


if __name__ == "__main__":
    asyncio.run(run_seed())
