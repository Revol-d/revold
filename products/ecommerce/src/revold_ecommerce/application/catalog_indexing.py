"""Reindexação do catálogo para o índice vetorial do assistente de IA.

Orquestração entre domínios: lê o catálogo (ProductRepository) e escreve no
assistente (via IndexProduct). Nenhum dos dois domínios importa o outro
(ADR-0002), então essa composição é do produto (ADR-0027). É o equivalente
em lote de revold_ecommerce.application.stock, que compõe domínios a cada
requisição. Quem chama: o catalog-indexer (o catálogo inteiro), o
event-worker (um SKU, a cada `product.updated`) e o api-gateway (o endpoint
administrativo de reindexação).
"""
from __future__ import annotations

from revold_ai_assistant.application.use_cases import IndexProduct
from revold_catalog.ports import ProductRepository

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


async def reindex_one_product(
    sku: str,
    product_repository: ProductRepository,
    index_product: IndexProduct,
) -> bool:
    """Reindexa um único produto — usado pelo handler do evento
    `product.updated` (ver apps/ecommerce/event-worker, ADR-0013), bem mais barato
    que reindexar o catálogo inteiro a cada edição.

    Retorna False (sem levantar erro) se o produto não existe mais no
    catálogo — o evento pode ter sido publicado e só processado depois do
    produto ter sido removido; não é um erro do worker, é uma corrida
    esperada entre publicação e consumo assíncronos.
    """
    product = await product_repository.get_product(sku)
    if product is None:
        return False
    await index_product.execute(sku=product.sku, name=product.name, description=product.description)
    return True
