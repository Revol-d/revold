# Build context: raiz do monorepo (docker-compose.yml usa "context: .").
# Este Dockerfile serve tanto o dev (target dev, com reload) quanto o
# runtime que vira a imagem publicada para o Container App (ADR-0004),
# para que o mesmo ambiente Python 3.12 seja usado em todo lugar — nunca
# mais depender da versão de Python instalada na máquina de quem está
# desenvolvendo (ver decisão "sempre usar Docker").
FROM python:3.12-slim AS base

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
COPY cores ./cores
COPY adapters ./adapters
COPY apps/api-gateway ./apps/api-gateway

RUN poetry install --only main

FROM base AS dev
RUN poetry install --with dev
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--app-dir", "apps/api-gateway/src"]

FROM base AS runtime
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api-gateway/src"]
