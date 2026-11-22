"""Seleciona a implementação de StoreSettingsRepository pelo nome do provedor de
persistência.

Este é o único lugar que decide qual adapter usar — trocar de provedor é mudar a
configuração (`PERSISTENCE_PROVIDER`), nunca importar um adapter diferente manualmente em
outro módulo.

Diferente de `build_llm_provider`/`build_identity_provider`, este factory não monta client
nem lê credencial: a `session` (SQLAlchemy async, já ligada ao engine do dialeto certo) vem
pronta de `dependencies.py` — aqui só se decide qual classe de repositório embrulha essa
sessão. Ver o plano de migração Postgres -> Azure SQL (docs internos) para o porquê de só
persistência ainda não ter esse factory (estava "sempre Postgres" por ADR-0019/0023/0024).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_store_settings.ports import StoreSettingsRepository

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_store_settings_repository(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> StoreSettingsRepository:
    if provider == "postgres":
        from revold_store_settings.adapters.postgres.repository import (
            PostgresStoreSettingsRepository,
        )

        return PostgresStoreSettingsRepository(session)
    if provider == "azure-sql":
        from revold_store_settings.adapters.azure_sql.repository import (
            AzureSqlStoreSettingsRepository,
        )

        return AzureSqlStoreSettingsRepository(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
