# Guia de Desenvolvimento

## Pré-requisito único: Docker
Por decisão de arquitetura (ADR-0009), todo o desenvolvimento local roda em containers Docker — a máquina de quem desenvolve só precisa ter Docker instalado (Docker Desktop no Windows/Mac, ou Docker Engine no Linux). A versão de Python/Node da máquina não importa: o Dockerfile de cada app fixa Python 3.12 / Node 20, os mesmos usados em CI e produção.

## Primeiros passos
1. `cp .env.example .env`
2. `make dev` — builda as imagens (primeira vez) e sobe Postgres, Redis, api-gateway (com reload), `worker` (consumidor de eventos, ADR-0013), Prometheus, Grafana e storefront (com hot reload) via `docker compose`.
3. `make migrate` (em outro terminal, com os serviços já de pé) — aplica as migrações Alembic dentro do container do api-gateway.
4. Storefront em http://localhost:3000, API em http://localhost:8000 (docs automáticas em `/docs`, geradas pelo FastAPI), admin-dashboard em http://localhost:3001, Prometheus em http://localhost:9090, Grafana em http://localhost:3002 (login anônimo habilitado, só em dev).

## Convenção de portas e adapters
Todo core define portas (interfaces Python, `Protocol` ou ABC) para qualquer dependência externa (banco, fila, serviço de terceiro). Adapters implementam essas portas em `adapters/`. Um adapter de desenvolvimento ("fake"/"sandbox") deve existir para qualquer integração externa que ainda não tenha credencial real disponível (ex.: `core-identity` antes de ter app registration do Azure AD/Google, checkout antes da WhatsApp Business API oficial) — isso permite construir e testar o sistema inteiro mesmo com liberações externas pendentes. A troca entre adapter de desenvolvimento e adapter real é sempre configuração (variável de ambiente), nunca mudança de código no core.

## Rodando comandos (sempre via Docker — ADR-0009)
- Testes: `make test` (ou `make test-unit`, `make test-integration`, `make test-contract`, `make test-eval` — ver ADR-0012 para o que cada camada cobre e quando pula sozinha em vez de falhar)
- Lint: `make lint`
- Formatação: `make format`
- Nunca rodar `poetry run`/`pnpm` direto na máquina — os `Makefile` targets já encapsulam o `docker compose run` correto.

## Estratégia de testes (ADR-0012)
Quatro camadas, cada teste marcado com `@pytest.mark.<nome>` (registrados em `pyproject.toml`) exceto a unitária, que é o padrão sem marker nenhum:
- **Unitário**: lógica pura ou contra fake em memória — roda sempre.
- **Fábricas de dados** (`revold_testing`, `tools/testing/`): Factory Boy + Faker (`pt_BR`) para gerar dado realista (acento, emoji, preço quebrado) em vez de só fixture manual — usadas dentro dos testes unitários/integração, não é uma camada à parte. Um módulo por core (`catalog_factories`, `cart_factories`, `inventory_factories`, `identity_factories`, `notification_factories`, `store_settings_factories`, `events_factories`, ver ADR-0012).
- **`@pytest.mark.integration`**: contra Postgres/pgvector real, não fake — pula sozinho sem `DATABASE_URL`/`TEST_DATABASE_URL` alcançável. Roda também no CI (service do GitHub Actions), não só localmente.
- **Sandbox de serviço externo** (`respx`, ou um emulador/servidor real self-hosted): todo adapter real que ainda não tem credencial de produção é validado contra algo que fala o protocolo de verdade, sem credencial nenhuma — `respx` simula a API HTTP do Azure OpenAI; o **Azurite** (emulador oficial da Microsoft) valida o `AzureBlobStorage` (ADR-0015); um worker Celery + Redis reais (subprocesso) validam o barramento de eventos de ponta a ponta (ADR-0013); o **aiosmtpd** (servidor SMTP real, em memória, puro Python) valida o `SmtpNotificationChannel` (ADR-0018).
- **`@pytest.mark.eval`** (`cores/core-ai-assistant/evals/`): dataset comportamental do assistente de IA. `test_behavior.py` roda sempre (determinístico, sem credencial). `test_llm_judge.py` (LLM-as-judge, nota de qualidade) só roda de verdade com `LLM_PROVIDER=azure-openai` real — pula sozinho caso contrário.
- **E2E** (`make test-e2e`, ADR-0020): Playwright, contra storefront + api-gateway + Postgres/Redis reais (a stack inteira de `make dev` já de pé) — `apps/storefront/e2e/global-setup.ts` semeia categoria/produto/estoque via chamadas HTTP reais antes da suíte, `checkout.spec.ts` cobre navegar → adicionar ao carrinho → fechar pedido pelo WhatsApp, e busca full-text de ponta a ponta.

## Leafs/adapters adicionados depois do MVP inicial (ADR-0013 a ADR-0018)

Enquanto credenciais de nuvem reais (Azure AD, Google, WhatsApp Business API, Azure OpenAI real) seguem indisponíveis, o framework foi enriquecido com leafs genéricos e reutilizáveis, 100% testados sem nenhuma credencial nova:

- **Barramento de eventos** (`core-events`, ADR-0013): `EventPublisher`/`DomainEvent` centralizados — evita cada core inventar seu próprio formato de evento e cair em problema de deduplicação. `EVENT_PUBLISHER=memory|celery`.
- **Busca full-text** (ADR-0014): Postgres nativo (`tsvector`+`unaccent`), sem porta nova.
- **Upload de imagem / blob storage** (`MediaStorage`, ADR-0015): `MEDIA_STORAGE_PROVIDER=local|azure-blob`.
- **API pública/parceiro** (ADR-0016): `ApiKeyAuth`/`RateLimiter` (`core-identity`) + `WebhookSender` (`core-events`) — `POST/DELETE /api/auth/api-keys` (RBAC ADMIN) para emitir/revogar chave, `GET /api/public/v1/products` como primeiro endpoint protegido por `X-API-Key`.
- **Observabilidade** (`MetricsPublisher`, `core-observability`, ADR-0017): `GET /metrics` (Prometheus), serviços `prometheus`/`grafana` no compose.
- **Canal de e-mail** (`SmtpNotificationChannel`, ADR-0018): `NOTIFICATION_PROVIDER=smtp`.

Ver `claude/planejamento-leafs-e-adaptadores.md` (Project) para o plano original e `docs/architecture/adr/0013-*.md` a `0018-*.md` para os registros completos.

## Configuração da loja e testes E2E (ADR-0019, ADR-0020)

- **Configuração da loja** (`core-store-settings`, ADR-0019): CNPJ, contato, dados da loja e o limiar de estoque baixo (antes só `LOW_STOCK_THRESHOLD`, fixo até deploy) agora são editáveis pela Nick em `/configuracoes` no admin-dashboard (RBAC ADMIN only) — `GET/PUT /api/store-settings`.
- **Testes E2E** (Playwright, ADR-0020): `make test-e2e` cobre o fluxo real de cliente ponta a ponta. Achado ao implementar: `docker-compose.yml` não carregava `.env` nos containers de `api-gateway`/`worker` (corrigido com `env_file`) e `SESSION_COOKIE_SECURE=true` por padrão quebrava login em `make dev` (sem HTTPS local) — `.env.example` agora usa `false` por padrão, `true` em produção (HTTPS real via Container Apps).

## Dashboards Grafana (ADR-0017)

`http://localhost:3002` já abre com o dashboard **"Revold — Visão Geral"** carregado — datasource Prometheus e dashboard são provisionados como código (`docker/grafana/provisioning/`), sem passo manual de configuração. Três seções: checkouts criados (taxa/min + total), alertas de estoque baixo (taxa/min + total), e API (requisições por status, taxa de erro 5xx, latência p50/p95/p99). Para adicionar um painel novo, editar `docker/grafana/provisioning/dashboards/json/revold-overview.json` (recarregado a cada 30s) em vez de só ajustar pela UI — a UI permite editar (`allowUiUpdates: true`), mas o arquivo do repositório é a fonte de verdade e sobrescreve no próximo reload.

## Convenção de commits
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` — branch a partir de `develop`, PR com quality gates locais rodando antes de abrir.
