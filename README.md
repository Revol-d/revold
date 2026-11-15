# revold

Monorepo de um e-commerce e das bibliotecas que ele usa. A loja é o primeiro produto; a estrutura
existe para o que é genérico (identidade, pagamentos, catálogo, notificação) servir ao próximo.

É um **monolito modular**: 27 unidades num repositório só, cada uma com dono, versão e fronteira
conferida por ferramenta.

- **Vai contribuir?** Comece pelo [CONTRIBUTING.md](CONTRIBUTING.md): da máquina zerada ao release.
- **Quer entender a estrutura?** [docs/ARQUITETURA.md](docs/ARQUITETURA.md) (a referência curta) e
  a [aula de arquitetura](docs/onboarding/arquitetura-monorepo.md) (o porquê de cada regra).
- **É uma IA?** [AGENTS.md](AGENTS.md).

## Começar

```powershell
git clone https://github.com/SamuelSMatos/revold.git
cd revold

uv sync                                   # todas as unidades Python e as ferramentas de dev
pre-commit install
pre-commit install --hook-type pre-push

uv run dev check                          # manifesto, fronteiras e tipos
uv run dev test -q                        # a suíte inteira
```

Para ver o sistema funcionando (precisa de Docker):

```powershell
Copy-Item .env.example .env
make dev                                  # Postgres, Redis, API, worker, sites, Prometheus, Grafana
make migrate
make seed                                 # catálogo de demonstração
```

Loja em http://localhost:3000, painel em http://localhost:3001, API em http://localhost:8000/docs.
O que instalar antes e o que fazer quando algo trava: [CONTRIBUTING.md](CONTRIBUTING.md), seção 2.

## O mapa

```text
apps/ecommerce/        o que sobe sozinho: api-gateway, event-worker, catalog-indexer,
                       storefront, admin-dashboard
products/ecommerce/    o que cruza dois ou mais domínios; os contratos da API; as migrações
libs/
  platform/            configuração, eventos de domínio, observabilidade
  integrations/        clientes de sistema externo: postgres, redis, messaging, prometheus,
                       smtp, whatsapp, mercado-pago, openai, azure-blob
  domains/             um bounded context cada: catalog, cart, inventory, orders, payments,
                       identity, notification, communication, store-settings, ai-assistant
  web/ui/              os componentes de interface dos sites
tooling/               a CLI `uv run dev`
deploy/                Terraform (Azure) e a observabilidade local
tests/                 os gates de arquitetura e o apoio de teste compartilhado
docs/                  arquitetura, decisões (ADR), base de conhecimento
.releases/             o BOM de cada release de app
```

A seta de dependência só desce: app → produto → domínio → integração → plataforma. Domínio não
importa domínio, e app não importa app. Cada unidade tem um `unit.yaml`, e o `README.md` dela diz o
que ela faz e o que ela **não** faz.

## Stack

| Parte | Tecnologia |
|---|---|
| API e workers | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, Celery |
| Dados | PostgreSQL 16 com pgvector, Redis 7 |
| Assistente de IA | LangGraph; Azure OpenAI ou DeepSeek, com um provedor de desenvolvimento sem credencial |
| Sites | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Observabilidade | Prometheus e Grafana |
| Ferramental | uv (workspace e lock único), pnpm, ruff, mypy, import-linter, pytest, Playwright |
| Infraestrutura | Docker Compose na máquina; Azure Container Apps como alvo (Terraform escrito, ainda não aplicado) |

Todo serviço externo (login, pagamento, e-mail, WhatsApp, LLM, armazenamento de imagem) tem um
adapter de desenvolvimento: o sistema inteiro roda e é testado sem credencial nenhuma.

## Comandos do dia a dia

| Quero… | Comando |
|---|---|
| Conferir tudo antes de abrir PR | `uv run dev check` e `uv run dev test --affected -q` |
| Rodar a suíte inteira | `uv run dev test -q` |
| Lint | `uv run ruff check .` |
| Ver o que a branch afeta | `uv run dev affected` |
| Criar uma unidade | `uv run dev new <kind> <id> --depends-on <ids> --dry-run` |
| Regenerar `.importlinter` e CODEOWNERS | `uv run dev gen` |
| Subir a versão de uma unidade | `uv run dev bump <unidade> patch` |
| Fazer o release de um app | `uv run dev release <app> patch --dry-run` |
| Subir a pilha | `make dev` |
| Lint e build dos sites | `pnpm lint` e `pnpm build` |

A lista completa da CLI: [tooling/README.md](tooling/README.md).

## Como se trabalha aqui

- Uma branch protegida só, a `main`. Todo trabalho sai dela numa branch curta e volta por PR, com
  squash merge ([docs/branch-strategy.md](docs/branch-strategy.md)).
- Issue antes de código; um PR por issue, uma unidade por PR.
- Hooks locais, um check agregado no CI (`CI OK`) e aprovação de um dono (CODEOWNERS).
- Cada unidade tem a própria versão; o app só sobe no release
  ([docs/versionamento-e-deploy.md](docs/versionamento-e-deploy.md)).
- Sem emoji e sem IA como co-autora em commit e PR; o uso de IA se declara no template de PR.

## O que ainda não existe

Nenhum ambiente publicado, nenhum release, e o ruleset do GitHub ainda não foi aplicado. A lista
honesta do que os gates ainda não cobrem está na seção 13 do [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentação

| Documento | Para quê |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | o passo a passo completo |
| [AGENTS.md](AGENTS.md) | as regras para IA (e para pessoas) |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | os tipos de unidade e as regras |
| [docs/onboarding/arquitetura-monorepo.md](docs/onboarding/arquitetura-monorepo.md) | a aula, com o porquê |
| [docs/branch-strategy.md](docs/branch-strategy.md) | branches, CI, CODEOWNERS |
| [docs/versionamento-e-deploy.md](docs/versionamento-e-deploy.md) | versão, release, imagem |
| [docs/guides/development.md](docs/guides/development.md) | a pilha local e a estratégia de testes |
| [docs/kb/](docs/kb/README.md) | base de conhecimento e as [decisões](docs/kb/decisoes/README.md) |
| [docs/security/README.md](docs/security/README.md), [SECURITY.md](SECURITY.md) | segurança |
| [docs/planejamento-inicial.md](docs/planejamento-inicial.md) | o texto de planejamento original: visão, objetivos e roadmap |

## Licença

Projeto proprietário. Todos os direitos reservados.
