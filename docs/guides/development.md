# Guia de Desenvolvimento

## Pré-requisitos
Python >= 3.12, Node.js >= 18, Poetry >= 1.7, pnpm >= 8 (via `corepack enable`), Docker (para Postgres/Redis locais).

## Primeiros passos
1. `cp .env.example .env`
2. `docker compose up -d postgres redis`
3. `poetry install --with dev`
4. `pnpm install`
5. `poetry run alembic upgrade head`
6. `make dev`

## Convenção de portas e adapters
Todo core define portas (interfaces Python, `Protocol` ou ABC) para qualquer dependência externa (banco, fila, serviço de terceiro). Adapters implementam essas portas em `adapters/`. Um adapter de desenvolvimento ("fake"/"sandbox") deve existir para qualquer integração externa que ainda não tenha credencial real disponível (ex.: `core-identity` antes de ter app registration do Azure AD/Google, checkout antes da WhatsApp Business API oficial) — isso permite construir e testar o sistema inteiro mesmo com liberações externas pendentes. A troca entre adapter de desenvolvimento e adapter real é sempre configuração (variável de ambiente), nunca mudança de código no core.

## Convenção de commits
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` — branch a partir de `develop`, PR com quality gates locais rodando antes de abrir.
