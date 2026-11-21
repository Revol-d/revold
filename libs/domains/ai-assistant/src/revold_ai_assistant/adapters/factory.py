"""Seleciona a implementação de ProductIndex pelo nome do provedor de
persistência. Mesmo padrão de revold_store_settings.adapters.factory.

Não confundir com revold_ai_assistant.adapters.llm.factory.build_llm_provider
(dev/azure-openai/deepseek via LLM_PROVIDER) -- porta e fábrica diferentes do
mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_ai_assistant.ports import ProductIndex

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_product_index(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> ProductIndex:
    if provider == "postgres":
        from revold_ai_assistant.adapters.postgres.repository import (
            PostgresProductIndexRepository,
        )

        return PostgresProductIndexRepository(session)
    if provider == "azure-sql":
        from revold_ai_assistant.adapters.azure_sql.repository import (
            AzureSqlProductIndexRepository,
        )

        return AzureSqlProductIndexRepository(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
