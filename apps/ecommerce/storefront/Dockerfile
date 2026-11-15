# Build context: raiz do monorepo (precisa de libs/web/ui via workspace pnpm).
#
#   docker build --target runtime -f apps/ecommerce/storefront/Dockerfile -t revold/storefront .
#
# As pastas entram com o mesmo caminho que têm no repositório: o pnpm-workspace.yaml e o
# pnpm-lock.yaml citam `apps/ecommerce/storefront` e `libs/web/ui`.
FROM node:20-slim AS base
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY libs/web ./libs/web
COPY apps/ecommerce/storefront ./apps/ecommerce/storefront
RUN pnpm install --frozen-lockfile
WORKDIR /repo/apps/ecommerce/storefront

FROM base AS dev
# Sem navegador aqui: os testes E2E (Playwright) rodam na máquina ou no runner do CI, contra
# esta loja de pé. Rodando de dentro do container, o navegador não alcançaria a API em
# NEXT_PUBLIC_API_GATEWAY_URL (localhost:8000), que só existe do lado de fora.
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
