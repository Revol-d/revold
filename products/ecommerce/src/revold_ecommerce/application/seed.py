"""Seed semântico da loja (ADR-0022): os casos de uso que populam um banco vazio.

O que isto faz e por quê:

1. Só existe pra popular um banco vazio (ou recém-migrado, ex. depois de
   `make clean`/`docker compose down -v`) com um catálogo coerente e
   apresentável — sem isto, avaliar se o storefront "está bom" não dá,
   porque toda página de listagem simplesmente não tem nada pra mostrar
   (e, com a degradação graciosa do storefront, nem aparenta erro — só
   mostra uma vitrine vazia, o que é pior pra avaliação porque parece "não
   tem bug" quando na verdade não tem DADO).

2. Nunca faz INSERT cru: monta os mesmos objetos de domínio
   (`revold_catalog.domain.Product`, etc.) que uma chamada real de admin
   geraria e persiste através das portas de repositório — as invariantes
   de domínio (`Money` não aceita negativo, `StoreSettings` valida
   CNPJ/e-mail, etc.) continuam valendo automaticamente, sem o seed
   precisar reimplementá-las.

3. É idempotente por CONSTRUÇÃO, não por sorte: nunca sobrescreve o que
   já existe.
     - Categoria/produto: só cria se ainda não existir (checa por
       slug/SKU antes). Rodar `make seed` de novo depois que a Nick já
       editou a descrição de um produto semeado NÃO desfaz a edição dela
       — isto é seed de baseline, não sincronização contínua.
     - Estoque: só ENTRA a diferença até o alvo (nunca reduz, nunca
       duplica) — a entrada de estoque é aditiva por natureza, então rodar
       de novo sem checar antes dobraria o estoque a cada execução.
     - Configuração da loja: só grava se ainda não houver nenhum registro
       (`StoreSettingsRepository.get() is None`) — depois que a Nick
       preencher os dados de verdade em `/configuracoes`, `make seed`
       nunca mais toca neste registro.

4. Contrato de extensão (o motivo de existir um módulo central, ver
   ADR-0022): cada domínio com dado de demonstração relevante expõe, em
   `libs/domains/<dominio>/src/revold_<dominio>/seed.py`, as constantes
   que descreve melhor (aqui `revold_catalog.seed.CATEGORIES`/`PRODUCTS` e
   `revold_store_settings.seed.DEMO_SETTINGS`). Este módulo só conhece a
   ORDEM de dependência entre domínios (categoria antes de produto,
   produto antes de estoque) — nunca o conteúdo do dado em si. Adicionar
   seed pra um domínio novo é: escrever o `seed.py` dele seguindo este
   mesmo formato e registrar uma função `seed_<nome>` abaixo.

Este módulo é do produto porque cruza domínios (catálogo, estoque e
configuração da loja), e nenhum domínio importa outro (ADR-0002). Ele só
recebe portas: quem monta os repositórios reais e imprime o resultado é o
app (`python -m api_gateway.seed`, chamado por `make seed`).
"""

from __future__ import annotations

from dataclasses import dataclass

from revold_catalog import seed as catalog_seed
from revold_catalog.ports import ProductRepository
from revold_inventory.domain import StockLevel
from revold_inventory.ports import InventoryRepository
from revold_store_settings import seed as store_settings_seed
from revold_store_settings.ports import StoreSettingsRepository


@dataclass(frozen=True)
class CatalogSeedResult:
    """Quanto o seed do catálogo criou nesta execução."""

    categories_created: int
    products_created: int
    variants_created: int
    stock_topped_up: int


async def seed_catalog(
    product_repository: ProductRepository, inventory_repository: InventoryRepository
) -> CatalogSeedResult:
    """Cria as categorias, os produtos e o estoque inicial que ainda não existem."""
    categories_created = 0
    for category in catalog_seed.CATEGORIES:
        if await product_repository.get_category(category.slug) is None:
            await product_repository.save_category(category)
            categories_created += 1

    products_created = 0
    variants_created = 0
    stock_topped_up = 0
    for seed_product in catalog_seed.PRODUCTS:
        existing = await product_repository.get_product(seed_product.sku)
        if existing is not None:
            continue
        product_category = await product_repository.get_category(seed_product.category_slug)
        if product_category is None:
            raise ValueError(
                f"CATEGORIES não tem '{seed_product.category_slug}' — "
                f"produto '{seed_product.sku}' referencia uma categoria que o "
                f"seed nem declara, corrija revold_catalog/seed.py"
            )
        await product_repository.save_product(seed_product.to_domain(product_category))
        products_created += 1
        variants_created += len(seed_product.variants)

        for variant in seed_product.variants:
            current = await inventory_repository.get(variant.variant_sku)
            on_hand = current.quantity_on_hand if current is not None else 0
            missing = variant.initial_stock - on_hand
            if missing > 0:
                stock = current or StockLevel(sku=variant.variant_sku)
                stock.receive(missing)
                await inventory_repository.save(stock)
                stock_topped_up += 1

    return CatalogSeedResult(
        categories_created=categories_created,
        products_created=products_created,
        variants_created=variants_created,
        stock_topped_up=stock_topped_up,
    )


async def seed_store_settings(repository: StoreSettingsRepository) -> bool:
    """Grava a configuração de demonstração se ainda não houver nenhuma. Devolve se gravou."""
    if await repository.get() is not None:
        return False
    await repository.save(store_settings_seed.DEMO_SETTINGS)
    return True


def format_seed_report(catalog: CatalogSeedResult, *, settings_created: bool) -> list[str]:
    """As linhas do relatório que o app imprime ao fim do seed."""
    lines = [
        "Seed semântico (ADR-0022) concluído:",
        f"  categorias criadas .......... {catalog.categories_created}"
        f" (de {len(catalog_seed.CATEGORIES)} declaradas)",
        f"  produtos criados ............ {catalog.products_created}"
        f" (de {len(catalog_seed.PRODUCTS)} declarados)",
        f"  variantes criadas junto ...... {catalog.variants_created}",
        f"  entradas de estoque aplicadas  {catalog.stock_topped_up}",
        "  configuração da loja ........ "
        + (
            "criada (dado placeholder — editar em /configuracoes)"
            if settings_created
            else "já existia, mantida"
        ),
    ]
    if catalog.categories_created == 0 and catalog.products_created == 0 and not settings_created:
        lines.append(
            "  (nada novo — banco já estava semeado; make seed nunca sobrescreve dado existente)"
        )
    return lines
