.PHONY: dev setup clean test test-unit test-integration test-contract test-eval test-e2e coverage lint format check build migrate ci-local seed

# Dois jeitos de rodar comando neste repositório, cada um com o seu papel (ADR-0031):
#
# - Os GATES do dia a dia (manifesto, fronteiras, lint, testes sem infraestrutura) rodam na
#   máquina, pelo uv: `uv run dev check`, `uv run dev test`. São eles que os hooks de
#   pre-commit e o CI chamam. Ver CONTRIBUTING.md, seções 2 e 5.
# - A PILHA (Postgres, Redis, API, worker, sites, Prometheus, Grafana) roda em container,
#   pelos alvos abaixo. Assim ninguém depende da versão de Postgres/Node instalada na máquina,
#   e os testes de integração e E2E falam com serviço de verdade (ADR-0009).
#
# Dentro do container do api-gateway o ambiente Python já está no PATH (/opt/venv): os
# comandos são chamados direto, sem `uv run`.

setup:
	docker compose build

dev:
	docker compose up --build

clean:
	docker compose down -v --rmi local

test:
	docker compose run --rm api-gateway pytest
	docker compose run --rm storefront pnpm test

test-unit:
	docker compose run --rm api-gateway pytest -m "not integration and not e2e"

test-integration:
	docker compose run --rm api-gateway pytest -m integration

test-contract:
	docker compose run --rm api-gateway pytest -m contract

test-eval:
	docker compose run --rm api-gateway pytest -m eval -v

# Os testes E2E rodam na máquina, contra a pilha de pé (`make dev` em outro terminal, e
# `make migrate` uma vez). O navegador precisa alcançar a loja e a API pelas portas publicadas
# (3000 e 8000), e de dentro de um container elas não são localhost. Na primeira vez:
# `pnpm install` e `pnpm --filter storefront exec playwright install chromium`.
test-e2e:
	pnpm --filter storefront exec playwright test

coverage:
	docker compose run --rm api-gateway pytest --cov --cov-report=term-missing

lint:
	docker compose run --rm api-gateway ruff check .
	docker compose run --rm api-gateway dev check
	docker compose run --rm storefront pnpm lint

format:
	docker compose run --rm api-gateway ruff format .

# O gate único (manifesto, gerados em dia, versões, fronteiras e mypy) dentro do container.
# Na máquina, o mesmo gate é `uv run dev check`.
check:
	docker compose run --rm api-gateway dev check

migrate:
	docker compose run --rm api-gateway alembic upgrade head

# Popula um banco vazio (ou recém-migrado) com um catálogo semântico —
# categorias/produtos/estoque/configuração da loja escritos à mão, coerentes
# o bastante pra apresentar pra Nick (ADR-0022) — nunca dado aleatório de
# Faker (isso é `tests/support`, feito pra teste automatizado, não demo).
# Idempotente: rodar de novo não duplica nem sobrescreve o que já existe
# (dado de exemplo, ou já editado de verdade pela Nick no admin). Rodar
# sempre depois de `make migrate` num banco novo — sem isto, dá pra
# avaliar se o CI/build está passando, mas não dá pra avaliar como o site
# fica de verdade, porque toda página de listagem estará vazia.
# --build: sem isto, "docker compose run" reaproveita a imagem já
# existente mesmo que o uv.lock ou um pyproject.toml tenham mudado desde o
# último build (dependência nova, unidade nova). Com --build, o Docker só
# refaz as camadas que de fato mudaram (cache normal), então o custo extra
# é baixo quando nada mudou.
seed:
	docker compose run --build --rm api-gateway python -m api_gateway.seed

# As imagens de runtime de cada app, com a tag local `revold/<app>`. O release de verdade
# passa por `uv run dev release <app>` e pelo release.yml (CONTRIBUTING.md, seção 8).
build:
	docker build --target runtime -f apps/ecommerce/api-gateway/Dockerfile -t revold/api-gateway .
	docker build --target runtime -f apps/ecommerce/event-worker/Dockerfile -t revold/event-worker .
	docker build --target runtime -f apps/ecommerce/catalog-indexer/Dockerfile -t revold/catalog-indexer .
	docker build --target runtime -f apps/ecommerce/storefront/Dockerfile -t revold/storefront .
	docker build --target runtime -f apps/ecommerce/admin-dashboard/Dockerfile -t revold/admin-dashboard .

# Roda .github/workflows/ci.yml localmente via `act` (requer instalar o
# binário `act` — Docker já é pré-requisito da pilha, ADR-0009).
# Diferente de `make test`/`make lint` acima: aqueles rodam dentro do
# container da aplicação (docker compose run --rm ...); este roda nas
# condições do runner de CI de verdade (bare, sem .env, sem os volumes/
# environment do docker-compose.yml) — é o que pega bug do tipo "só
# quebra no CI" (ver ADR-0021) antes do push.
ci-local:
	act pull_request
