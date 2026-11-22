# Imagem do api-gateway. O contexto do build é a RAIZ do monorepo, porque o `uv sync` precisa
# do workspace inteiro (o uv.lock e o pyproject.toml de cada membro):
#
#   docker build --target runtime -f apps/ecommerce/api-gateway/Dockerfile -t revold/api-gateway .
#
# Este Dockerfile serve tanto o dev (target dev, com reload) quanto o runtime que vira a imagem
# publicada para o Container App (ADR-0004), para que o mesmo Python 3.12 seja usado em todo
# lugar. O `.dockerignore` da raiz deixa de fora .venv, node_modules e o .git.
FROM python:3.12-slim AS base

# Driver ODBC do SQL Server: pyodbc/aioodbc exigem a biblioteca do sistema, nao so
# o pacote Python -- sem isso o container sobe mas qualquer conexao com o Azure SQL
# falha ("Can't open lib ... No such file or directory"). Confirmado rodando a
# instalacao de verdade contra esta mesma imagem base antes de aplicar aqui:
# python:3.12-slim e Debian (nao Ubuntu, diferente do runner do CI), entao usa o
# repositorio oficial da Microsoft para Debian, lendo a versao de /etc/os-release
# em vez de fixar uma.
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
# para o reload não escondem as dependências instaladas.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock .python-version alembic.ini ./
# Todo membro do workspace uv precisa existir para o lock ser lido, mesmo o que esta imagem não
# instala: por isso entram o tooling e os três apps Python.
COPY tooling ./tooling
COPY libs ./libs
COPY products ./products
COPY apps/ecommerce/api-gateway ./apps/ecommerce/api-gateway
COPY apps/ecommerce/event-worker ./apps/ecommerce/event-worker
COPY apps/ecommerce/catalog-indexer ./apps/ecommerce/catalog-indexer

# Usado pelo docker-compose (condition: service_healthy) para o
# storefront/admin-dashboard só tentarem falar com a API depois que o
# Uvicorn realmente estiver de pé — sem isso, um fetch server-side do
# Next.js logo depois do `docker compose up` pode chegar antes da API subir
# e falhar com "fetch failed" (conexão recusada), mesmo com a URL certa.
HEALTHCHECK --interval=5s --timeout=5s --retries=20 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Dev: o workspace inteiro com o grupo `dev`, para `make test`, `make lint` e `make migrate`
# rodarem dentro do container. A suíte central (tests/) entra só aqui.
FROM base AS dev
COPY tests ./tests
RUN uv sync --frozen --all-packages
EXPOSE 8000
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Runtime: só o api-gateway e o fecho dele (o que o unit.yaml declara), sem o grupo `dev`.
FROM base AS runtime
RUN uv sync --frozen --no-default-groups --package api-gateway
EXPOSE 8000
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
