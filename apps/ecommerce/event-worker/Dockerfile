# Imagem do event-worker. O contexto do build é a RAIZ do monorepo, porque o `uv sync` precisa
# do workspace inteiro (o uv.lock e o pyproject.toml de cada membro):
#
#   docker build --target runtime -f apps/ecommerce/event-worker/Dockerfile -t revold/event-worker .
#
# Até a reorganização em apps/products/libs este worker rodava na imagem do api-gateway, só com
# outro comando. Agora cada app tem a própria imagem, com o próprio fecho (ADR-0027).
FROM python:3.12-slim AS base

# Driver ODBC do SQL Server (ver api-gateway/Dockerfile para o porque e a
# verificacao -- mesma instalacao, repetida aqui porque cada app tem a propria
# imagem).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg2 apt-transport-https unixodbc-dev \
    && debian_version=$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2) \
    && curl -fsSLO "https://packages.microsoft.com/config/debian/${debian_version}/packages-microsoft-prod.deb" \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv
# O ambiente fica em /opt/venv, fora de /app: os volumes que o docker-compose monta em /app
# para o desenvolvimento não escondem as dependências instaladas.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
# Todo membro do workspace uv precisa existir para o lock ser lido, mesmo o que esta imagem não
# instala: por isso entram o tooling e os três apps Python.
COPY tooling ./tooling
COPY libs ./libs
COPY products ./products
COPY apps/ecommerce/api-gateway ./apps/ecommerce/api-gateway
COPY apps/ecommerce/event-worker ./apps/ecommerce/event-worker
COPY apps/ecommerce/catalog-indexer ./apps/ecommerce/catalog-indexer

FROM base AS dev
RUN uv sync --frozen --package event-worker
CMD ["celery", "-A", "event_worker.celery_app", "worker", "--loglevel=info"]

# Runtime: só o event-worker e o fecho dele (o que o unit.yaml declara), sem o grupo `dev`.
FROM base AS runtime
RUN uv sync --frozen --no-default-groups --package event-worker
CMD ["celery", "-A", "event_worker.celery_app", "worker", "--loglevel=info"]
