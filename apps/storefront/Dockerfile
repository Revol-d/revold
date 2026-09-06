# Build context: raiz do monorepo (precisa de packages/ui via workspace).
FROM node:20-slim AS base
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages ./packages
COPY apps/storefront ./apps/storefront
RUN pnpm install --frozen-lockfile
WORKDIR /repo/apps/storefront

FROM base AS dev
# Chromium + libs de sistema pro Playwright (ADR-0020, testes E2E) — só
# paga esse custo o stage de dev, usado por `make test-e2e`/`make lint`/
# `make test`; o stage de runtime (produção) não carrega nada disso.
RUN pnpm exec playwright install --with-deps chromium
EXPOSE 3000
CMD ["pnpm", "dev"]

# Otimização futura: usar `output: "standalone"` do Next.js para uma imagem
# de runtime menor (sem precisar do node_modules completo). Não feito agora
# para manter o Dockerfile simples e verificável nesta primeira versão.
FROM base AS runtime
RUN pnpm build
ENV NODE_ENV=production
EXPOSE 3000
CMD ["pnpm", "start"]
