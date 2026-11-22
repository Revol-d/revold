"""Monta a implementação de ProductIndex contra o Azure SQL Database. Mesmo padrão
de revold_store_settings.adapters.factory. Postgres foi removido (Fase 7 do plano
de migração Postgres -> Azure SQL, docs internos).

Não confundir com revold_ai_assistant.adapters.llm.factory.build_llm_provider
(dev/azure-openai/deepseek via LLM_PROVIDER) -- porta e fábrica diferentes do
mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_ai_assistant.adapters.azure_sql.repository import AzureSqlProductIndexRepository
from revold_ai_assistant.ports import ProductIndex


def build_product_index(session: AsyncSession) -> ProductIndex:
    return AzureSqlProductIndexRepository(session)
