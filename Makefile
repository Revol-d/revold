.PHONY: dev setup clean test test-unit test-integration test-contract test-e2e coverage lint format build migrate

# Convenção do projeto: todo comando roda dentro de container Docker, nunca
# direto na máquina de quem desenvolve — evita "funciona na minha máquina"
# por causa de versão de Python/Node divergente (ver docs/guides/development.md).

setup:
	docker compose build

dev:
	docker compose up --build

clean:
	docker compose down -v --rmi local

test:
	docker compose run --rm api-gateway poetry run pytest
	docker compose run --rm storefront pnpm test

test-unit:
	docker compose run --rm api-gateway poetry run pytest -m "not integration and not e2e"

test-integration:
	docker compose run --rm api-gateway poetry run pytest -m integration

test-contract:
	docker compose run --rm api-gateway poetry run pytest -m contract

test-e2e:
	docker compose run --rm storefront pnpm exec playwright test

coverage:
	docker compose run --rm api-gateway poetry run pytest --cov --cov-report=term-missing

lint:
	docker compose run --rm api-gateway poetry run ruff check .
	docker compose run --rm api-gateway poetry run mypy .
	docker compose run --rm storefront pnpm lint

format:
	docker compose run --rm api-gateway poetry run ruff format .

migrate:
	docker compose run --rm api-gateway poetry run alembic upgrade head

build:
	docker build --target runtime -f apps/api-gateway/Dockerfile -t revold/api-gateway .
	docker build --target runtime -f apps/storefront/Dockerfile -t revold/storefront .
