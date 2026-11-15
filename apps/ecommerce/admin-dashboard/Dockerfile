# Build context: raiz do monorepo (workspace pnpm).
#
#   docker build --target runtime -f apps/ecommerce/admin-dashboard/Dockerfile -t revold/admin-dashboard .
#
# As pastas entram com o mesmo caminho que têm no repositório: o pnpm-workspace.yaml e o
# pnpm-lock.yaml citam `apps/ecommerce/admin-dashboard` e `libs/web/ui`.
FROM node:20-slim AS base
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY libs/web ./libs/web
COPY apps/ecommerce/admin-dashboard ./apps/ecommerce/admin-dashboard
RUN pnpm install --frozen-lockfile
WORKDIR /repo/apps/ecommerce/admin-dashboard

FROM base AS dev
EXPOSE 3001
CMD ["pnpm", "dev"]

FROM base AS runtime
RUN pnpm build
ENV NODE_ENV=production
EXPOSE 3001
CMD ["pnpm", "start"]
