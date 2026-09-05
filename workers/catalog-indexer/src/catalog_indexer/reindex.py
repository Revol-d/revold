"""Reindexação do catálogo para o índice vetorial do core-ai-assistant.

Cross-core orchestration: lê core-catalog (ProductRepository) e escreve em
core-ai-assistant (via IndexProduct) — nenhum dos dois cores importa o
outro (ADR-0002), então essa composição vive aqui. É o equivalente batch
de apps/api_gateway/orchestration.py (que compõe cores a cada requisição);
esta função compõe em lote, por isso mora em workers/.
"""
from __future__ import annotations

from core_ai_assistant.use_cases import IndexProduct
from core_catalog.ports import ProductRepository

_DEFAULT_PAGE_SIZE = 50


async def reindex_all_products(
    product_repository: ProductRepository,
    index_product: IndexProduct,
    *,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> int:
    """Reindexa todo o catálogo, paginando via list_products.

    Retorna quantos produtos foram indexados.
    """
    page = 1
    indexed = 0
    while True:
        items, total = await product_repository.list_products(
            category_slug=None, page=page, page_size=page_size
        )
        if not items:
            break
        for product in items:
            await index_product.execute(
                sku=product.sku, name=product.name, description=product.description
            )
            indexed += 1
        if page * page_size >= total:
            break
        page += 1
    return indexed
