# ADR-0009: Docker-first para desenvolvimento local

**Status:** Aceito

## Contexto
A máquina de desenvolvimento tem Python 3.10, enquanto a arquitetura (ADR de stack, `pyproject.toml`) exige Python 3.12. Atualizar o Python da máquina resolveria só este sintoma — o próximo desenvolvedor, ou uma segunda máquina, teria o mesmo problema com outra versão divergente (Python, Node, etc.). Decisão explícita: em vez de manter a máquina local sincronizada manualmente com as versões exigidas, usar Docker como o único jeito de rodar o projeto localmente.

## Decisão
`apps/api-gateway/Dockerfile` e `apps/storefront/Dockerfile` são multi-stage, cada um com um target `dev` (usado pelo `docker-compose.yml`, com volume mount do código-fonte e hot-reload/`--reload`) e um target `runtime` (usado para build de produção, a mesma imagem que sobe no Container App do Terraform — ADR-0004). Isso significa que dev, e o que roda em produção, usam a mesma base de imagem — não só "parece igual", é a mesma definição.

`make dev`, `make test`, `make lint`, `make format`, `make migrate` — todos os comandos do dia a dia — rodam via `docker compose run`/`docker compose up`, nunca `poetry run`/`pnpm` direto na máquina. A máquina local só precisa ter Docker instalado; a versão de Python/Node dela deixa de importar.

CI (GitHub Actions, ADR-0008) segue o mesmo princípio: builda as mesmas imagens Docker e roda os testes dentro delas, em vez de instalar Python/Node diretamente no runner — a mesma imagem é testada em CI, rodada em dev e publicada em produção.

## Consequências
- Todo novo desenvolvedor (ou agente de IA trabalhando no código) só precisa de Docker instalado — não precisa instalar/gerenciar Python 3.12 nem pnpm/Node na própria máquina.
- Build de imagem tem um custo de tempo que rodar direto na máquina não tem — mitigado por cache de camada Docker (o `poetry install`/`pnpm install` só reroda quando `pyproject.toml`/`package.json` mudam, não a cada alteração de código, graças à ordem das camadas no Dockerfile).
- `poetry.lock` e `pnpm-lock.yaml` passam a ser gerados e mantidos via Docker (rodando `poetry lock` dentro de um container), nunca localmente com uma versão de Python diferente da exigida.
