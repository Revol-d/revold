# Decisões registradas (ADRs)

Toda decisão arquitetural relevante (unidade nova que muda a estrutura, mudança de infraestrutura,
troca de provedor externo, mudança de fluxo de trabalho) ganha uma ADR **antes** da implementação,
não depois. Modelo: [../templates/decisao-padrao.md](../templates/decisao-padrao.md).

Numeração sequencial, com quatro dígitos. Confira esta tabela antes de abrir um número novo.

> **As ADRs 0001 a 0026 descrevem o repositório como ele era** quando cada uma foi decidida: citam
> `cores/`, `adapters/`, `workers/` e os pacotes `core_*`. Elas não foram reescritas na
> reorganização, de propósito: são o registro do que valia. O de/para entre os nomes antigos e os
> de hoje está na [0027](0027-estrutura-apps-products-libs.md).

| ADR | Título | Situação |
|---|---|---|
| [0001](0001-estrategia-de-monorepo.md) | Estratégia de Monorepo | a organização de pastas foi revisada pela 0027 |
| [0002](0002-separacao-em-cores.md) | Separação em Cores (Bounded Contexts) | os contextos valem; a pasta `cores/` virou `libs/domains/` (0027) |
| [0003](0003-autenticacao-federada-sem-senha-propria.md) | Autenticação federada, sem senha própria | |
| [0004](0004-plataforma-de-execucao-azure.md) | Plataforma de execução no Azure (Container Apps) | |
| [0005](0005-checkout-manual-via-whatsapp.md) | Checkout manual via WhatsApp, com porta para automação futura | |
| [0006](0006-provedor-de-llm-azure-openai-langgraph.md) | Provedor de LLM: Azure OpenAI + LangGraph | |
| [0007](0007-frontend-orientado-a-composicao.md) | Frontend orientado a composição (sem ferramenta de design) | |
| [0008](0008-ci-no-github-actions.md) | CI/CD no GitHub Actions | o gatilho e os gates foram revisados pela 0028 |
| [0009](0009-docker-first-para-desenvolvimento-local.md) | Docker-first para desenvolvimento local | revisada pela 0031 |
| [0010](0010-sessao-via-cookie-httponly-redis.md) | Sessão de autenticação via cookie HttpOnly + Redis | |
| [0011](0011-escopo-do-assistente-de-ia.md) | Escopo do assistente de IA (RAG sobre catálogo + LangGraph) | |
| [0012](0012-estrategia-de-testes-dados-realistas-e-evals.md) | Estratégia de testes: dados realistas, sandbox de serviço externo e evals | |
| [0013](0013-core-events-e-barramento-de-eventos.md) | core-events e barramento de eventos (Celery/Redis) | hoje em `revold_platform.events` e `libs/integrations/messaging` |
| [0014](0014-busca-full-text-tsvector.md) | Busca full-text de produtos (tsvector + unaccent) | |
| [0015](0015-media-blob-storage.md) | MediaStorage: upload de imagem de produto (blob storage) | |
| [0016](0016-api-key-rate-limit-webhook-outbound.md) | API key + rate limiter + webhook de saída | |
| [0017](0017-observabilidade-metricas-prometheus.md) | Observabilidade: métricas (Prometheus/Grafana) | hoje em `revold_platform.observability` e `libs/integrations/prometheus` |
| [0018](0018-canal-de-notificacao-email-smtp.md) | Canal de notificação por e-mail (SMTP) | |
| [0019](0019-core-store-settings-configuracao-da-loja.md) | core-store-settings: configuração da loja editável | |
| [0020](0020-testes-e2e-playwright.md) | Testes E2E com Playwright | hoje rodam no CI e na máquina, fora do container (CONTRIBUTING, seção 10) |
| [0021](0021-reproducao-local-do-ci-e-correcao-de-falhas-so-reproduziveis-no-runner.md) | Reprodução local do CI (`act`) e correção de duas falhas que só apareciam no runner | |
| [0022](0022-processo-padrao-de-seed-semantico.md) | Processo padrão de seed semântico | o orquestrador está em `revold_ecommerce.application.seed` (0027) |
| [0023](0023-core-orders-gestao-de-pedidos.md) | core-orders: pedido persistido como pré-requisito de pagamento | |
| [0024](0024-core-payments-pix-e-cartao.md) | core-payments: cobrança Pix real, cartão deliberadamente adiado | |
| [0025](0025-whatsapp-business-notification-channel.md) | Canal de notificação por WhatsApp Business | |
| [0026](0026-deepseek-como-llm-provider-de-chat-embeddings-continuam-na-azure.md) | DeepSeek como provedor de chat; embeddings continuam na Azure | |
| [0027](0027-estrutura-apps-products-libs.md) | Estrutura `apps/`, `products/`, `libs/` e os tipos de unidade | implementado |
| [0028](0028-trunk-based-e-release-por-app.md) | Trunk-based com release por app | decidido; o ruleset ainda não foi aplicado |
| [0029](0029-workspace-uv-versao-por-unidade-e-lock-unico.md) | Workspace uv, versão por unidade e um lock só | implementado |
| [0030](0030-tooling-proprio-e-manifesto-unit-yaml.md) | Tooling próprio (`dev`) e o manifesto `unit.yaml` | implementado |
| [0031](0031-gates-na-maquina-pilha-em-container.md) | Gates na máquina, pilha em container | implementado |
| [0032](0032-migracao-postgres-para-azure-sql.md) | Migração de Postgres para Azure SQL Database | implementado |
