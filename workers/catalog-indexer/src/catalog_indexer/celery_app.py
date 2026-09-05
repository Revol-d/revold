"""Tarefa Celery de reindexação periódica do catálogo (produção).

Não testado com um worker Celery de verdade nesta sessão — precisaria de
Redis e um worker rodando, que este ambiente não tem. A lógica em si
(reindex_all_products) é testada isoladamente com fakes em test_reindex.py;
este módulo só monta as dependências reais (Postgres, o LLMProvider
configurado via LLM_PROVIDER) e chama a mesma função. Agendar
`reindex_catalog_task` periodicamente (ex. Celery beat, diariamente) fica
para quando houver infraestrutura de produção — por enquanto o mesmo
código também é chamado de forma síncrona pelo endpoint administrativo
POST /api/assistant/reindex.
"""
from __future__ import annotations

import asyncio
import os

from celery import Celery

from adapters_external.ai.factory import get_llm_provider
from adapters_persistence.ai_assistant.repository import PostgresProductIndexRepository
from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from core_ai_assistant.use_cases import IndexProduct

from catalog_indexer.reindex import reindex_all_products

celery_app = Celery(
    "catalog_indexer",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)


async def _reindex() -> int:
    engine = make_engine()
    session_factory = make_session_factory(engine)
    llm = get_llm_provider()
    async with session_factory() as session:
        product_repository = PostgresProductRepository(session)
        index_repository = PostgresProductIndexRepository(session)
        index_product = IndexProduct(llm, index_repository)
        return await reindex_all_products(product_repository, index_product)


@celery_app.task(name="catalog_indexer.reindex_catalog")
def reindex_catalog_task() -> int:
    return asyncio.run(_reindex())
