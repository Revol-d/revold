.PHONY: dev setup clean test test-unit test-integration test-contract test-e2e coverage lint format build

setup:
	poetry install --with dev
	pnpm install

dev:
	docker compose up -d postgres redis
	poetry run uvicorn api_gateway.main:app --reload --app-dir apps/api-gateway/src --port 8000 &
	pnpm --filter storefront dev

clean:
	docker compose down -v
	rm -rf .venv node_modules apps/*/node_modules apps/*/.next

test:
	poetry run pytest

test-unit:
	poetry run pytest -m "not integration and not e2e"

test-integration:
	poetry run pytest -m integration

test-contract:
	poetry run pytest -m contract

test-e2e:
	pnpm --filter storefront exec playwright test

coverage:
	poetry run pytest --cov --cov-report=term-missing

lint:
	poetry run ruff check .
	poetry run mypy .
	pnpm -r lint

format:
	poetry run ruff format .

build:
	pnpm -r build

migrate:
	poetry run alembic upgrade head
