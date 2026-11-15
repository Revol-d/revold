---
tags: [decisao, ambiente, docker, uv, hooks]
status: implementado
escopo: plataforma
resumo: Os gates do dia a dia rodam na maquina, pelo uv e pelos hooks; a pilha (banco, fila, API, sites) continua em container
cobre: [Makefile, docker-compose.yml, .pre-commit-config.yaml, apps/ecommerce/api-gateway/Dockerfile]
---

# 0031 — Gates na máquina, pilha em container

**Data:** 2026-11 (reorganização do monorepo)
**Revisa:** [0009](0009-docker-first-para-desenvolvimento-local.md)

## Contexto

A 0009 decidiu que **todo** comando roda em container: a máquina só precisa de Docker, e ninguém
depende da versão de Python ou de Node instalada. O guia dizia para nunca rodar `poetry run` nem
`pnpm` direto na máquina.

Dois fatos pesam contra aplicar isso a tudo:

- **Hook de git roda na máquina.** O `pre-commit` e o `pre-push` são o primeiro gate do fluxo novo
  ([0028](0028-trunk-based-e-release-por-app.md)). Um hook que sobe container a cada commit é lento
  o bastante para todo mundo pular.
- **O CI já rodava fora de container**, direto no runner, e essa diferença já tinha escondido dois
  defeitos ([0021](0021-reproducao-local-do-ci-e-correcao-de-falhas-so-reproduziveis-no-runner.md)).
  O ambiente da máquina com `uv sync` é mais parecido com o do CI do que o container da aplicação.

A preocupação original da 0009, a versão de Python divergente, o `uv` resolve: ele instala o Python
do `.python-version` e trava tudo pelo `uv.lock`.

## Opções

1. **Tudo em container (a 0009)** — um pré-requisito só; hook lento ou sem hook.
2. **Tudo na máquina** — exige Postgres, Redis e Node instalados e na versão certa em cada máquina.
3. **Gates na máquina, pilha em container (escolhida).**

## Decisão

Opção 3.

- **Na máquina, pelo `uv`:** `uv run dev check`, `uv run dev test`, `uv run ruff check`, os hooks.
  São os mesmos comandos do CI. Não precisam de banco: os testes marcados `integration` pulam
  sozinhos.
- **Em container, pelo `make` e pelo Docker Compose:** Postgres, Redis, a API, o worker, os sites,
  Prometheus e Grafana; as migrações, o seed e os testes E2E. É onde se vê o sistema funcionando.
- **Os alvos do `Makefile` continuam existindo** e continuam rodando em container, para quem
  preferir o caminho da 0009.

## Consequências

- **O pré-requisito deixa de ser só o Docker**: entram `uv` e `pre-commit` (e Node com pnpm, para
  quem mexe nos sites). O passo a passo está no CONTRIBUTING, seção 2.
- **As imagens passam a usar `uv`**, com o ambiente em `/opt/venv`, fora de `/app`, para os volumes
  de desenvolvimento não esconderem as dependências.
- **Um teste que só passava com Postgres de pé, sem estar marcado `integration`, foi corrigido**
  (`test_metrics_endpoint`): na máquina, sem a pilha, ele falhava em vez de pular.
- **Rodar os testes de integração na máquina** é subir só o banco e a fila em container e apontar
  os testes para eles (CONTRIBUTING, seção 10).
- **O `make ci-local` (act) continua valendo** como aproximação do runner.
