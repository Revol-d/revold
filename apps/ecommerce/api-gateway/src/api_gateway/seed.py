"""Ponto de entrada de `python -m api_gateway.seed` (ver `make seed`, ADR-0022).

Monta as dependências reais (Postgres ou Azure SQL, via `PERSISTENCE_PROVIDER` --
mesmo padrão de `api_gateway.dependencies`) e chama os casos de uso de
`revold_ecommerce.application.seed`, que é onde a regra do seed mora. Roda no container do
api-gateway porque é ele que já tem o banco e os repositórios configurados.
"""

from __future__ import annotations

import asyncio

from api_gateway.settings import database_url, persistence_provider
from revold_catalog.adapters.factory import build_product_repository
from revold_ecommerce.application.seed import format_seed_report, seed_catalog, seed_store_settings
from revold_inventory.adapters.factory import build_inventory_repository
from revold_store_settings.adapters.factory import build_store_settings_repository


async def run_seed() -> None:
    provider = persistence_provider()
    if provider == "azure-sql":
        from revold_azure_sql.db import make_engine, make_session_factory
    else:
        from revold_postgres.db import make_engine, make_session_factory

    engine = make_engine(database_url())
    session_factory = make_session_factory(engine)
    try:
        async with session_factory() as session:
            catalog = await seed_catalog(
                build_product_repository(session, provider),
                build_inventory_repository(session, provider),
            )
            settings_created = await seed_store_settings(
                build_store_settings_repository(session, provider)
            )
    finally:
        await engine.dispose()

    for line in format_seed_report(catalog, settings_created=settings_created):
        print(line)


if __name__ == "__main__":
    asyncio.run(run_seed())
