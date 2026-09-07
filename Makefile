.PHONY: dev setup clean test test-unit test-integration test-contract test-eval test-e2e coverage lint format build migrate ci-local seed

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

test-eval:
	docker compose run --rm api-gateway poetry run pytest -m eval -v

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

# Popula um banco vazio (ou recém-migrado) com um catálogo semântico —
# categorias/produtos/estoque/configuração da loja escritos à mão, coerentes
# o bastante pra apresentar pra Nick (ADR-0022) — nunca dado aleatório de
# Faker (isso é `tools/testing`, feito pra teste automatizado, não demo).
# Idempotente: rodar de novo não duplica nem sobrescreve o que já existe
# (dado de exemplo, ou já editado de verdade pela Nick no admin). Rodar
# sempre depois de `make migrate` num banco novo — sem isto, dá pra
# avaliar se o CI/build está passando, mas não dá pra avaliar como o site
# fica de verdade, porque toda página de listagem estará vazia.
# --build: sem isto, "docker compose run" reaproveita a imagem já
# existente mesmo que pyproject.toml/tools/ tenham mudado desde o último
# build (ex.: o próprio módulo revold_seed sendo adicionado agora) — achado
# rodando de verdade pela primeira vez ("No module named revold_seed" numa
# imagem construída antes deste commit). Com --build, o Docker só refaz as
# camadas que de fato mudaram (cache normal), então o custo extra é baixo
# quando nada mudou.
seed:
	docker compose run --build --rm api-gateway poetry run python -m revold_seed

build:
	docker build --target runtime -f apps/api-gateway/Dockerfile -t revold/api-gateway .
	docker build --target runtime -f apps/storefront/Dockerfile -t revold/storefront .

# Roda .github/workflows/ci.yml localmente via `act` (requer instalar o
# binário `act` — Docker já é pré-requisito único do projeto, ADR-0009).
# Diferente de `make test`/`make lint` acima: aqueles rodam dentro do
# container da aplicação (docker compose run --rm ...); este roda nas
# condições do runner de CI de verdade (bare, sem .env, sem os volumes/
# environment do docker-compose.yml) — é o que pega bug do tipo "só
# quebra no CI" (ver ADR-0021) antes do push.
ci-local:
	act pull_request
