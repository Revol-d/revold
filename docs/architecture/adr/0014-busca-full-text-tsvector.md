# ADR-0014: busca full-text de produtos (tsvector + unaccent)

**Status:** Aceito

## Contexto

A busca de catálogo (`GET /api/catalog/products?q=...`) era um `ILIKE '%termo%'` simples contra `name`. Duas limitações reais:

1. Sem tolerância a acento/plural/gênero: buscar "ocasiao" nunca casava com "ocasião", "camiseta" nunca casava com "camisetas".
2. Sem noção de relevância: `sort=relevance` na prática ordenava por SKU — não existia nenhum critério de "quão bem o produto casa com a busca".

Isso é 100% resolvível com infraestrutura self-hosted (Postgres, que já está no `docker-compose.yml`) — não depende de nenhuma credencial externa nem serviço novo.

## Decisão

Full-text search nativo do Postgres em vez de um serviço de busca separado (Meilisearch/Typesense, cogitados no planejamento original): o catálogo já vive no Postgres, o volume de produtos não justifica um serviço dedicado agora, e menos peças móveis é preferível enquanto um segundo caso de uso não aparece para confirmar que vale a pena.

- **Coluna gerada** `catalog_products.search_vector` (`tsvector`, `GENERATED ALWAYS ... STORED`, migration 0004): o Postgres recalcula sozinho a cada mudança de `name`/`description` — nenhum código de aplicação nem trigger precisa manter isso sincronizado.
- **Configuração de busca `pt_unaccent`**: copia `portuguese` (stemming de plural/gênero/conjugação) e troca o dicionário de palavra para normalizar acento via a extensão `unaccent` — "camisêta"/"camisetas" casam com "camiseta" na mesma busca.
- **Índice GIN** sobre `search_vector` para a busca não degradar com o crescimento do catálogo.
- `sort=relevance` com `search_query` presente ordena por `ts_rank` (quão bem o produto casa), não mais por SKU.

A porta `ProductRepository.list_products` **não mudou** — o `search_query` já existia como parâmetro; só a implementação Postgres ficou melhor. Nenhuma outra camada (use case, router, storefront) precisou mudar.

## Testes

`adapters/persistence/tests/test_catalog_repository_integration.py` (`@pytest.mark.integration`, contra Postgres real): busca por palavra exata (regressão do comportamento anterior), tolerância a falta de acento, tolerância a plural, e ordenação por relevância com dois produtos que casam de formas diferentes.

## Consequências

- Busca do catálogo (storefront e admin) fica mais tolerante sem nenhuma mudança de contrato ou de frontend.
- Índice GIN adiciona um custo pequeno de escrita (recalcular o `tsvector` a cada save) — aceitável no volume atual do catálogo.
- Se o catálogo crescer a ponto de precisar de facetas, sinônimos ou busca federada entre múltiplos projetos do framework, um serviço dedicado (Meilisearch) continua sendo uma opção — a porta não muda, só a implementação.
