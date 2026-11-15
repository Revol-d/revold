# A pilha local e a estratégia de testes

> O passo a passo de trabalho (ferramentas, branch, commit, PR, release) é o
> [CONTRIBUTING.md](../../CONTRIBUTING.md). Este guia detalha duas coisas que lá aparecem em resumo:
> a pilha que roda em container e o que cada camada de teste cobre.

## Onde cada coisa roda

Desde a [ADR-0031](../kb/decisoes/0031-gates-na-maquina-pilha-em-container.md), há dois lugares:

| O quê | Onde | Como |
|---|---|---|
| Gates: manifesto, fronteiras, tipos, lint, testes sem infraestrutura | na máquina | `uv run dev check`, `uv run dev test`, `uv run ruff check .`, e os hooks |
| A pilha: banco, fila, API, worker, sites, métricas | em container | `make dev` |
| Migrações, seed, testes de integração e E2E | em container, ou na máquina apontando para o banco em container | `make migrate`, `make seed`, `make test-integration`, `make test-e2e` |

A [ADR-0009](../kb/decisoes/0009-docker-first-para-desenvolvimento-local.md) mandava rodar **tudo**
em container. Os alvos do [Makefile](../../Makefile) continuam fazendo isso, para quem preferir.

## Primeiros passos com a pilha

1. `Copy-Item .env.example .env`
2. `make dev`: monta as imagens (na primeira vez) e sobe Postgres, Redis, o api-gateway (com
   reload), o `worker` (o event-worker, [ADR-0013](../kb/decisoes/0013-core-events-e-barramento-de-eventos.md)),
   Prometheus, Grafana, a loja e o painel.
3. `make migrate` (em outro terminal, com os serviços já de pé): aplica as migrações Alembic dentro
   do container do api-gateway.
4. `make seed`: popula um banco vazio com um catálogo coerente, estoque e a configuração da loja.
   Sem este passo a loja sobe, mas toda página de listagem fica vazia, sem erro nenhum
   ([ADR-0022](../kb/decisoes/0022-processo-padrao-de-seed-semantico.md)). Seguro rodar de novo:
   nunca duplica nem sobrescreve dado que já existe.
5. Loja em http://localhost:3000, API em http://localhost:8000 (documentação em `/docs`), painel em
   http://localhost:3001, Prometheus em http://localhost:9090, Grafana em http://localhost:3002
   (login anônimo, só em desenvolvimento).

Trocou dependência ou criou unidade? Refaça a imagem (`make setup`): o `docker compose run`
reaproveita a imagem velha sem avisar.

## Portas, adapters e o adapter de desenvolvimento

Todo domínio declara portas (`Protocol`) para qualquer dependência externa, e os adapters que as
implementam moram na camada `adapters/` do próprio domínio ([docs/ARQUITETURA.md](../ARQUITETURA.md),
seção 4). **Toda integração externa tem um adapter de desenvolvimento** (fake, log ou disco local)
além do real, para o sistema inteiro rodar e ser testado antes de existir credencial:

| Assunto | Variável | Desenvolvimento | Real |
|---|---|---|---|
| Login | `AUTH_PROVIDER` | `dev` | `azure-ad`, `google` (ainda sem adapter, [ADR-0003](../kb/decisoes/0003-autenticacao-federada-sem-senha-propria.md)) |
| LLM | `LLM_PROVIDER` | `dev` | `azure-openai`, `deepseek` ([ADR-0011](../kb/decisoes/0011-escopo-do-assistente-de-ia.md), [ADR-0026](../kb/decisoes/0026-deepseek-como-llm-provider-de-chat-embeddings-continuam-na-azure.md)) |
| Pagamento | `PAYMENT_PROVIDER` | `fake` | `mercado_pago`, só Pix ([ADR-0024](../kb/decisoes/0024-core-payments-pix-e-cartao.md)) |
| Notificação | `NOTIFICATION_PROVIDER` | `logging` | `smtp`, `whatsapp-business` ([ADR-0018](../kb/decisoes/0018-canal-de-notificacao-email-smtp.md), [ADR-0025](../kb/decisoes/0025-whatsapp-business-notification-channel.md)) |
| Imagem de produto | `MEDIA_STORAGE_PROVIDER` | `local` | `azure-blob` ([ADR-0015](../kb/decisoes/0015-media-blob-storage.md)) |
| Eventos | `EVENT_PUBLISHER` | `memory` | `celery` ([ADR-0013](../kb/decisoes/0013-core-events-e-barramento-de-eventos.md)) |
| Webhook de saída | `WEBHOOK_SENDER_PROVIDER` | `logging` | `http` ([ADR-0016](../kb/decisoes/0016-api-key-rate-limit-webhook-outbound.md)) |

A lista completa, com o significado de cada variável, é o [.env.example](../../.env.example).

## Estratégia de testes (ADR-0012)

As camadas, cada uma marcada com `@pytest.mark.<nome>` (registrados no `pyproject.toml` da raiz),
menos a unitária, que é o padrão sem marcador:

- **Unitário**: regra pura ou contra fake em memória. Roda sempre.
- **Fábricas de dados** (`revold_testing`, em `tests/support/`): Factory Boy e Faker (`pt_BR`) para
  gerar dado realista (acento, preço quebrado) em vez de só fixture escrita à mão. Um módulo por
  domínio. São usadas dentro dos testes; não são uma camada à parte.
- **`integration`**: contra Postgres com pgvector, Redis ou um servidor de verdade em memória. Pula
  sozinho sem a infraestrutura alcançável. Roda no CI (com o Postgres do service) e na máquina com
  o banco em container (CONTRIBUTING, seção 10).
- **Sandbox de serviço externo**: todo adapter real sem credencial de produção é validado contra
  algo que fala o protocolo de verdade. `respx` simula a API HTTP do Azure OpenAI, do DeepSeek, do
  Mercado Pago e da Meta; o **Azurite** (emulador oficial) valida o `AzureBlobStorage`; o `aiosmtpd`
  valida o envio de e-mail; um worker Celery com Redis valida o round-trip de evento. O sandbox
  confere o **formato** documentado, não o comportamento real do serviço.
- **`contract`**: confere o api-gateway contra os contratos OpenAPI em
  `products/ecommerce/contracts/api/`. Hoje compara a lista de rotas (método e caminho) nas duas
  direções; os campos de requisição e resposta ainda não são conferidos.
- **`eval`** (`libs/domains/ai-assistant/evals/`): o dataset comportamental do assistente.
  `test_behavior.py` roda sempre (determinístico, sem credencial). `test_llm_judge.py` (LLM como
  juiz, nota de qualidade) só roda com `LLM_PROVIDER=azure-openai` e credencial real, e chama um
  serviço pago: pula sozinho caso contrário.
- **E2E** (`make test-e2e`, [ADR-0020](../kb/decisoes/0020-testes-e2e-playwright.md)): Playwright,
  contra a pilha de `make dev` já de pé, rodando **na máquina** (fora do container), como um
  cliente. O `global-setup.ts` semeia categoria, produto e estoque por chamadas HTTP reais antes
  da suíte. Roda também no CI, no job "E2E (Playwright)", quando a loja ou a API são afetadas.
- **Arquitetura** (`tests/architecture/`): os gates que conferem a estrutura do repositório
  ([docs/ARQUITETURA.md](../ARQUITETURA.md), seção 7).

## Painéis do Grafana (ADR-0017)

http://localhost:3002 já abre com o painel **"Revold — Visão Geral"** carregado: a fonte de dados e
o painel são provisionados como código (`deploy/observability/grafana/provisioning/`), sem passo
manual. As métricas vêm do endpoint `/metrics` do api-gateway.

## Reproduzir o CI na máquina (ADR-0021)

`uv run dev check` e `uv run dev test` na máquina já rodam os mesmos comandos do CI, no mesmo
ambiente travado pelo `uv.lock`. Para reproduzir o **runner** (sem `.env`, com o service do
Postgres):

1. Instale o [`act`](https://github.com/nektos/act).
2. `make ci-local`: roda o `ci.yml` em containers que emulam o runner do GitHub Actions. O `.actrc`
   usa uma imagem de runner leve.

O `act` é uma aproximação, não uma garantia de paridade com o runner hospedado.
