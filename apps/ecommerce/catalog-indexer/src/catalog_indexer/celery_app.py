"""Tarefa Celery de reindexação periódica do catálogo (produção).

Não testado com um worker Celery de verdade — precisaria de Redis e um
worker rodando. A lógica em si (reindex_all_products) mora no produto
(`revold_ecommerce.application.catalog_indexing`) e é testada isoladamente
com fakes em products/ecommerce/tests/test_catalog_indexing.py; este módulo
só monta as dependências reais (Azure SQL, o LLMProvider configurado via
LLM_PROVIDER) e chama a mesma função. Agendar `reindex_catalog_task`
periodicamente (ex. Celery beat, diariamente) fica para quando houver
infraestrutura de produção — por enquanto o mesmo código também é chamado
de forma síncrona pelo endpoint administrativo POST /api/assistant/reindex.

A configuração vem de `catalog_indexer.settings`, o único módulo do app que
lê o ambiente.
"""

from __future__ import annotations

import asyncio

from celery import Celery

from catalog_indexer import settings
from revold_ai_assistant.adapters.factory import build_product_index
from revold_ai_assistant.adapters.llm.factory import build_llm_provider
from revold_ai_assistant.application.use_cases import IndexProduct
from revold_catalog.adapters.factory import build_product_repository
from revold_ecommerce.application.catalog_indexing import reindex_all_products

celery_app = Celery("catalog_indexer", broker=settings.redis_url())


async def _reindex() -> int:
    from revold_azure_sql.db import make_engine, make_session_factory

    engine = make_engine(settings.database_url())
    session_factory = make_session_factory(engine)
    llm = build_llm_provider(settings.llm_settings())
    async with session_factory() as session:
        product_repository = build_product_repository(session)
        index_repository = build_product_index(session)
        index_product = IndexProduct(llm, index_repository)
        return await reindex_all_products(product_repository, index_product)


@celery_app.task(name="catalog_indexer.reindex_catalog")
def reindex_catalog_task() -> int:
    return asyncio.run(_reindex())
