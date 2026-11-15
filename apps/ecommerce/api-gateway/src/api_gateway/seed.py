"""Ponto de entrada de `python -m api_gateway.seed` (ver `make seed`, ADR-0022).

Só monta as dependências reais (Postgres) e chama os casos de uso de
`revold_ecommerce.application.seed`, que é onde a regra do seed mora. Roda no container do
api-gateway porque é ele que já tem o banco e os repositórios configurados.
"""

from __future__ import annotations

import asyncio

from api_gateway.settings import database_url
from revold_catalog.adapters.postgres.repository import PostgresProductRepository
from revold_ecommerce.application.seed import format_seed_report, seed_catalog, seed_store_settings
from revold_inventory.adapters.postgres.repository import PostgresInventoryRepository
from revold_postgres.db import make_engine, make_session_factory
from revold_store_settings.adapters.postgres.repository import PostgresStoreSettingsRepository


async def run_seed() -> None:
    engine = make_engine(database_url())
    session_factory = make_session_factory(engine)
    try:
        async with session_factory() as session:
            catalog = await seed_catalog(
                PostgresProductRepository(session), PostgresInventoryRepository(session)
            )
            settings_created = await seed_store_settings(PostgresStoreSettingsRepository(session))
    finally:
        await engine.dispose()

    for line in format_seed_report(catalog, settings_created=settings_created):
        print(line)


if __name__ == "__main__":
    asyncio.run(run_seed())
