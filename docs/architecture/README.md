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

Toda nova decisão arquitetural relevante (novo core, nova camada, mudança de infraestrutura, troca de provedor externo) deve ganhar um ADR novo antes da implementação, não depois.

## Regra de dependência entre camadas

```
apps/ e workers/  →  orchestrators/  →  cores/
adapters/ implementam portas definidas em cores/ (cores/ nunca importa de adapters/)
```

Ver `cores/core-catalog` como referência de implementação completa (contrato → domínio → porta → adapter → API → frontend).
