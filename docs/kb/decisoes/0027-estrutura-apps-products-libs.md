---
tags: [decisao, arquitetura, monorepo, estrutura]
status: implementado
escopo: plataforma
resumo: O repositorio passa a ser apps, products e libs, com tipos de unidade e regra de dependencia entre eles; cada core vira um dominio em libs/domains
cobre: [apps, products, libs, tooling/src/revold_tooling/manifest.py]
---

# 0027 — Estrutura `apps/`, `products/`, `libs/` e os tipos de unidade

**Data:** 2026-11 (reorganização do monorepo)
**Revisa:** [0001](0001-estrategia-de-monorepo.md) e [0002](0002-separacao-em-cores.md), só quanto
à organização de pastas. Os bounded contexts da 0002 continuam valendo.

## Contexto

O repositório era um pacote Python só (`[tool.poetry]` com 21 `packages`), organizado por papel
técnico: `cores/`, `adapters/`, `workers/`, `apps/`, `tools/`, `contracts/`, `packages/`. A regra
"cores não se importam" e "cores não importam adapters" estava escrita no README de arquitetura e em
comentário, e nenhuma ferramenta a conferia. Medido antes da mudança:

- os cores de fato não se importavam, o que tornou a reorganização viável;
- os três pacotes de `adapters/` eram **horizontais**: `adapters_persistence` importava oito cores e
  `adapters_external`, seis. Mexer no adapter de um contexto exigia instalar todos;
- dois apps importavam outro app: `api_gateway` e `event_worker` importavam `catalog_indexer` para
  reusar a reindexação;
- não havia fecho por app: a imagem do `api-gateway` carregava tudo, e o worker rodava nela com
  outro comando;
- a leitura de `os.environ` estava espalhada por dez módulos de `adapters/` (as factories, a
  conexão com o banco, o cliente Redis), além dos apps.

## Opções

1. **Manter `cores/` e `adapters/` e só acrescentar gates** — menor diff; os adapters horizontais
   continuariam impedindo o fecho por app, e a pasta `adapters/` de topo continuaria sendo o lugar
   sem dono para onde tudo vai.
2. **`apps/`, `products/`, `libs/` com um domínio por core (escolhida)** — cada bounded context vira
   uma unidade em `libs/domains/`, com os adapters dele dentro; o que cruza contextos vai para o
   produto; clientes de sistema externo viram `libs/integrations/`.
3. **Um único pacote de produto com todos os contextos por dentro** — menos unidades; perde o
   isolamento entre contextos que a 0002 estabeleceu e funde dez pacotes num só.

## Decisão

Opção 2, a mesma estrutura já usada em outro monorepo do time.

| Antes | Depois |
|---|---|
| `cores/core-<x>` (10 de negócio) | `libs/domains/<x>` (`revold_<x>`), com `adapters/`, `application/`, `ports/`, `domain/` |
| `cores/core-events`, `cores/core-observability` | `libs/platform` (`revold_platform.events`, `.observability`), mais `.configuration` |
| `adapters/persistence/<contexto>` | `libs/domains/<contexto>/…/adapters/postgres` ou `adapters/redis` |
| `adapters/persistence/db.py`, `redis_client.py` | `libs/integrations/postgres`, `libs/integrations/redis` |
| `adapters/external/<contexto>` | `adapters/` do domínio dono da porta; o cliente do serviço externo em `libs/integrations/{smtp,whatsapp,mercado-pago,openai,azure-blob,prometheus}` |
| `adapters/messaging` | `libs/integrations/messaging`; os adapters em memória, em `revold_platform.events` |
| `apps/api-gateway`, `workers/*` | `apps/ecommerce/{api-gateway,event-worker,catalog-indexer}` |
| `apps/storefront`, `apps/admin-dashboard` | `apps/ecommerce/{storefront,admin-dashboard}` |
| `api_gateway/orchestration.py`, `catalog_indexer/reindex.py`, `event_worker/dispatch.py`, `tools/seed` | `products/ecommerce` (`revold_ecommerce.application`) |
| `contracts/api`, `adapters/persistence/migrations` | `products/ecommerce/contracts/api`, `products/ecommerce/migrations` |
| `packages/ui` | `libs/web/ui` |
| `tools/testing` | `tests/support/revold_testing` |
| `iac/terraform`, `docker/` | `deploy/terraform`, `deploy/observability` |

A regra de dependência entre os tipos (D1) e as quatro perguntas que decidem se um código vai para
`libs/` estão em [docs/ARQUITETURA.md](../../ARQUITETURA.md), seção 3.

## Consequências

- **Domínio não importa domínio, e app não importa app**, agora por gate. O que precisa de dois
  domínios é do produto: foi para lá o que os apps compartilhavam.
- **Cada app tem o próprio fecho e a própria imagem.** O `event-worker` deixa de rodar na imagem do
  `api-gateway`: a imagem dele leva 15 unidades, a da API, 22.
- **Lib e produto não leem ambiente.** As factories de adapter recebem um objeto de configuração
  tipado; quem lê o ambiente é o `settings.py` de cada app.
- **Os nomes de import mudaram**: `core_catalog` virou `revold_catalog`, e `use_cases` e `schemas`
  foram para `application/`. As ADRs 0001 a 0026 citam os nomes e os caminhos antigos e não foram
  reescritas: são o registro do que valia quando foram decididas.
- **Ainda há regra de negócio nos routers do api-gateway.** Só a orquestração que já estava em
  módulo próprio foi para o produto (CONTRIBUTING, seção 13).
- **`libs/capabilities/` existe como tipo e ainda não tem unidade.**
