# Arquitetura

Este monorepo segue Domain-Driven Design, Hexagonal Architecture (Ports & Adapters), Clean Architecture e Contract-First Development — ver o README raiz para a visão geral.

## Decisões registradas (ADRs)

| ADR | Título |
|---|---|
| [0001](adr/0001-estrategia-de-monorepo.md) | Estratégia de Monorepo |
| [0002](adr/0002-separacao-em-cores.md) | Separação em Cores (Bounded Contexts) |
| [0003](adr/0003-autenticacao-federada-sem-senha-propria.md) | Autenticação federada, sem senha própria |
| [0004](adr/0004-plataforma-de-execucao-azure.md) | Plataforma de execução no Azure (Container Apps) |
| [0005](adr/0005-checkout-manual-via-whatsapp.md) | Checkout manual via WhatsApp, com porta para automação futura |
| [0006](adr/0006-provedor-de-llm-azure-openai-langgraph.md) | Provedor de LLM — Azure OpenAI + LangGraph |
| [0007](adr/0007-frontend-orientado-a-composicao.md) | Frontend orientado a composição (sem ferramenta de design) |
| [0008](adr/0008-ci-no-github-actions.md) | CI/CD no GitHub Actions |
| [0009](adr/0009-docker-first-para-desenvolvimento-local.md) | Docker-first para desenvolvimento local |
| [0010](adr/0010-sessao-via-cookie-httponly-redis.md) | Sessão de autenticação via cookie HttpOnly + Redis |
| [0011](adr/0011-escopo-do-assistente-de-ia.md) | Escopo do assistente de IA (RAG sobre catálogo + LangGraph) |
| [0012](adr/0012-estrategia-de-testes-dados-realistas-e-evals.md) | Estratégia de testes — dados realistas, sandbox de serviço externo, e evals de agente de IA |
| [0013](adr/0013-core-events-e-barramento-de-eventos.md) | core-events e barramento de eventos (Celery/Redis) |
| [0014](adr/0014-busca-full-text-tsvector.md) | Busca full-text de produtos (tsvector + unaccent) |
| [0015](adr/0015-media-blob-storage.md) | MediaStorage — upload de imagem de produto (blob storage) |
| [0016](adr/0016-api-key-rate-limit-webhook-outbound.md) | API key + rate limiter + webhook de saída (API pública/parceiro) |
| [0017](adr/0017-observabilidade-metricas-prometheus.md) | Observabilidade — métricas (Prometheus/Grafana) |
| [0018](adr/0018-canal-de-notificacao-email-smtp.md) | Canal de notificação por e-mail (SMTP) |
| [0019](adr/0019-core-store-settings-configuracao-da-loja.md) | core-store-settings — configuração da loja editável pela Nick |
| [0020](adr/0020-testes-e2e-playwright.md) | Testes E2E com Playwright |

Toda nova decisão arquitetural relevante (novo core, nova camada, mudança de infraestrutura, troca de provedor externo) deve ganhar um ADR novo antes da implementação, não depois.

## Regra de dependência entre camadas

```
apps/ e workers/  →  orchestrators/  →  cores/
adapters/ implementam portas definidas em cores/ (cores/ nunca importa de adapters/)
```

Ver `cores/core-catalog` como referência de implementação completa (contrato → domínio → porta → adapter → API → frontend).
