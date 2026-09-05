# Build context: raiz do monorepo (workspace pnpm).
FROM node:20-slim AS base
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages ./packages
COPY apps/admin-dashboard ./apps/admin-dashboard
RUN pnpm install --frozen-lockfile
WORKDIR /repo/apps/admin-dashboard

FROM base AS dev
EXPOSE 3001
CMD ["pnpm", "dev"]

FROM base AS runtime
RUN pnpm build
ENV NODE_ENV=production
EXPOSE 3001
CMD ["pnpm", "start"]
