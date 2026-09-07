"""Orquestrador do processo padrão de seed semântico (ADR-0022).

O que este script faz e por quê:

1. Só existe pra popular um banco vazio (ou recém-migrado, ex. depois de
   `make clean`/`docker compose down -v`) com um catálogo coerente e
   apresentável — sem isto, avaliar se o storefront "está bom" não dá,
   porque toda página de listagem simplesmente não tem nada pra mostrar
   (e, com a degradação graciosa do ADR mais recente sobre resiliência,
   nem aparenta erro — só mostra uma vitrine vazia, o que é pior pra
   avaliação porque parece "não tem bug" quando na verdade não tem DADO).

2. Nunca faz INSERT cru: monta os mesmos objetos de domínio
   (`core_catalog.domain.Product`, etc.) que uma chamada real de admin
   geraria e persiste através dos repositórios reais (mesma classe usada
   pelo api-gateway em produção) — as invariantes de domínio (`Money` não
   aceita negativo, `StoreSettings` valida CNPJ/e-mail, etc.) continuam
   valendo automaticamente, sem o seed precisar reimplementá-las. É o
   mesmo raciocínio que já justificava `apps/storefront/e2e/global-
   setup.ts` semear via chamada HTTP real em vez de INSERT — aqui é
   direto contra os repositórios (mais rápido, sem precisar de servidor
   HTTP nem login, já que isto roda como tarefa de desenvolvimento
   interna, não como simulação de uma ação da Nick).

3. É idempotente por CONSTRUÇÃO, não por sorte: nunca sobrescreve o que
   já existe.
     - Categoria/produto: só cria se ainda não existir (checa por
       slug/SKU antes). Rodar `make seed` de novo depois que a Nick já
       editou a descrição de um produto semeado NÃO desfaz a edição dela
       — isto é seed de baseline, não sincronização contínua.
     - Estoque: só ENTRA a diferença até o alvo (nunca reduz, nunca
       duplica) — `core_inventory.ReceiveStock` é aditivo por natureza
       (ver `core_inventory.use_cases.ReceiveStock`), então rodar de novo
       sem checar antes dobraria o estoque a cada execução.
     - Configuração da loja: só grava se ainda não houver nenhum registro
       (`StoreSettingsRepository.get() is None`) — depois que a Nick
       preencher os dados de verdade em `/configuracoes`, `make seed`
       nunca mais toca neste registro.

4. Contrato de extensão (o motivo de existir um módulo central, ver ADR-
   0022): cada core com dado de demonstração relevante expõe, em
   `cores/core-x/src/core_x/seed.py`, as constantes que descreve melhor
   (aqui `core_catalog.seed.CATEGORIES`/`PRODUCTS` e
   `core_store_settings.seed.DEMO_SETTINGS`). Este orquestrador só
   conhece a ORDEM de dependência entre cores (categoria antes de
   produto, produto antes de estoque) e como persistir cada um via seu
   próprio repositório — nunca o conteúdo do dado em si. Adicionar seed
   pra um core novo no futuro é: escrever o `seed.py` dele seguindo este
   mesmo formato e registrar uma função `_seed_<nome>` abaixo — nenhuma
   mudança no formato em si.
"""
from __future__ import annotations

import asyncio

from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from adapters_persistence.inventory.repository import PostgresInventoryRepository
from adapters_persistence.store_settings.repository import PostgresStoreSettingsRepository
from core_catalog import seed as catalog_seed
from core_inventory.domain import StockLevel
from core_store_settings import seed as store_settings_seed


async def _seed_catalog(session) -> tuple[int, int, int, int]:
    repo = PostgresProductRepository(session)

    categories_created = 0
    for category in catalog_seed.CATEGORIES:
        if await repo.get_category(category.slug) is None:
            await repo.save_category(category)
            categories_created += 1

    products_created = 0
    variants_created = 0
    stock_topped_up = 0
    inventory_repo = PostgresInventoryRepository(session)
    for seed_product in catalog_seed.PRODUCTS:
        existing = await repo.get_product(seed_product.sku)
        if existing is not None:
            continue
        product_category = await repo.get_category(seed_product.category_slug)
        assert product_category is not None, (
            f"CATEGORIES não tem '{seed_product.category_slug}' — "
            f"produto '{seed_product.sku}' referencia uma categoria que o "
            f"seed nem declara, corrija core_catalog/seed.py"
        )
        await repo.save_product(seed_product.to_domain(product_category))
        products_created += 1
        variants_created += len(seed_product.variants)

        for variant in seed_product.variants:
            current = await inventory_repo.get(variant.variant_sku)
            on_hand = current.quantity_on_hand if current is not None else 0
            missing = variant.initial_stock - on_hand
            if missing > 0:
                stock = current or StockLevel(sku=variant.variant_sku)
                stock.receive(missing)
                await inventory_repo.save(stock)
                stock_topped_up += 1

    return categories_created, products_created, variants_created, stock_topped_up


async def _seed_store_settings(session) -> bool:
    repo = PostgresStoreSettingsRepository(session)
    if await repo.get() is not None:
        return False
    await repo.save(store_settings_seed.DEMO_SETTINGS)
    return True


async def run_seed() -> None:
    engine = make_engine()
    session_factory = make_session_factory(engine)
    try:
        async with session_factory() as session:
            categories, products, variants, stock_topped_up = await _seed_catalog(session)
            settings_created = await _seed_store_settings(session)
    finally:
        await engine.dispose()

    print("Seed semântico (ADR-0022) concluído:")
    print(f"  categorias criadas .......... {categories} (de {len(catalog_seed.CATEGORIES)} declaradas)")
    print(f"  produtos criados ............ {products} (de {len(catalog_seed.PRODUCTS)} declarados)")
    print(f"  variantes criadas junto ...... {variants}")
    print(f"  entradas de estoque aplicadas  {stock_topped_up}")
    print(
        "  configuração da loja ........ "
        + ("criada (dado placeholder — editar em /configuracoes)" if settings_created else "já existia, mantida")
    )
    if categories == 0 and products == 0 and not settings_created:
        print("  (nada novo — banco já estava semeado; make seed nunca sobrescreve dado existente)")


if __name__ == "__main__":
    asyncio.run(run_seed())
