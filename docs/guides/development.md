# Guia de Desenvolvimento

## Pré-requisito único: Docker
Por decisão de arquitetura (ADR-0009), todo o desenvolvimento local roda em containers Docker — a máquina de quem desenvolve só precisa ter Docker instalado (Docker Desktop no Windows/Mac, ou Docker Engine no Linux). A versão de Python/Node da máquina não importa: o Dockerfile de cada app fixa Python 3.12 / Node 20, os mesmos usados em CI e produção.

## Primeiros passos
1. `cp .env.example .env`
2. `make dev` — builda as imagens (primeira vez) e sobe Postgres, Redis, api-gateway (com reload) e storefront (com hot reload) via `docker compose`.
3. `make migrate` (em outro terminal, com os serviços já de pé) — aplica as migrações Alembic dentro do container do api-gateway.
4. Storefront em http://localhost:3000, API em http://localhost:8000 (docs automáticas em `/docs`, geradas pelo FastAPI).

## Convenção de portas e adapters
Todo core define portas (interfaces Python, `Protocol` ou ABC) para qualquer dependência externa (banco, fila, serviço de terceiro). Adapters implementam essas portas em `adapters/`. Um adapter de desenvolvimento ("fake"/"sandbox") deve existir para qualquer integração externa que ainda não tenha credencial real disponível (ex.: `core-identity` antes de ter app registration do Azure AD/Google, checkout antes da WhatsApp Business API oficial) — isso permite construir e testar o sistema inteiro mesmo com liberações externas pendentes. A troca entre adapter de desenvolvimento e adapter real é sempre configuração (variável de ambiente), nunca mudança de código no core.

## Rodando comandos (sempre via Docker — ADR-0009)
- Testes: `make test` (ou `make test-unit`, `make test-integration`, `make test-contract`)
- Lint: `make lint`
- Formatação: `make format`
- Nunca rodar `poetry run`/`pnpm` direto na máquina — os `Makefile` targets já encapsulam o `docker compose run` correto.

## Convenção de commits
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` — branch a partir de `develop`, PR com quality gates locais rodando antes de abrir.
