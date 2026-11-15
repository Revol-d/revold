# Arquitetura do monorepo revold

> A referência curta: os tipos de unidade, a árvore, as regras de dependência e de camada, quem as
> fiscaliza e como criar uma unidade nova. A explicação longa, com o porquê de cada regra, um tour
> pelas unidades e os casos de contribuição, está na
> [aula de arquitetura](onboarding/arquitetura-monorepo.md). As decisões que sustentam isto são as
> ADRs 0027 a 0031, em [kb/decisoes/](kb/decisoes/README.md).
>
> Versão, build, release e deploy: [versionamento-e-deploy.md](versionamento-e-deploy.md).

---

## 1. A árvore

```text
revold/
├── apps/<produto>/<app>/      o que SOBE sozinho: API, worker, site (composition root)
├── products/<produto>/        o que é de UM produto: o que cruza dois ou mais domínios
├── libs/
│   ├── platform/              infraestrutura de todo app: configuração, eventos, observabilidade
│   ├── integrations/          cliente de UM sistema externo: postgres, smtp, mercado-pago
│   ├── capabilities/          mecanismo técnico sem dono de negócio (ainda sem unidade)
│   ├── domains/               um bounded context: catalog, cart, orders, payments
│   └── web/                   pacotes TypeScript: os componentes de interface
├── tooling/                   a CLI `dev`, os modelos do `dev new` e o schema do manifesto
├── deploy/                    como um app chega ao ambiente: Terraform e a observabilidade local
├── tests/                     testes do repositório inteiro (arquitetura) e o apoio de teste
├── scripts/                   utilitários que não são unidade (hook da main, rulesets)
├── docs/                      ADRs, KB, a aula
└── .releases/                 o BOM de cada release de app
```

Hoje há 27 unidades: cinco apps (três Python e dois sites), o produto `ecommerce`, dez domínios,
nove integrações, a plataforma e a lib web. A lista viva é o `unit.yaml` de cada uma;
`uv run dev version` mostra as Python.

## 2. A unidade e o manifesto

Toda pasta que é unidade tem um `unit.yaml` ao lado do código
([ADR-0030](kb/decisoes/0030-tooling-proprio-e-manifesto-unit-yaml.md)):

| Campo | O que diz |
|---|---|
| `id` | o nome da unidade (`catalog`, `api-gateway`) |
| `kind` | o tipo: `platform`, `integration`, `capability`, `domain`, `product`, `app`, `web` |
| `product` | a que produto pertence (só para `product` e `app`) |
| `language` | `python` ou `typescript` |
| `lifecycle` | `production`, `pilot`, `prototype` ou `deprecated`; app `production` não depende de `prototype` |
| `owners` | quem revisa |
| `depends_on` | as unidades que ela pode importar, e só essas |
| `pure_modules` | os módulos de uma integração sem I/O, que a `application/` de quem a usa pode importar |
| `stages` | as etapas da `application/`, de cima para baixo (opcional; nenhuma unidade usa hoje) |
| `runtime` | onde o app roda: `fastapi-api`, `celery-worker`, `cli`, `next-web` |
| `data.tables_owned` | as tabelas que a unidade grava (opcional; ainda não preenchido) |

O `.importlinter` e o `.github/CODEOWNERS` são **gerados** do manifesto (`uv run dev gen`); nunca se
editam à mão.

## 3. Os tipos e a regra entre eles (D1)

O `tooling` valida o `depends_on` de cada unidade contra esta tabela
(`ALLOWED_DEPENDENCY_KINDS`, em `tooling/src/revold_tooling/manifest.py`):

| A unidade é… | …pode depender de |
|---|---|
| `platform` | `platform` |
| `integration` | `platform` |
| `capability` | `platform`, `capability` |
| `domain` | `platform`, `capability`, `integration` (esta, só pela camada `adapters/`) |
| `product` | `platform`, `capability`, `integration`, `domain` |
| `app` | tudo, menos outro app |
| `web` (TypeScript) | `web` |

E o que nunca acontece: **domínio não importa domínio**; integração não importa integração nem
domínio; produto não importa produto; app não importa app; a camada `domain/` de qualquer unidade
não importa integração nenhuma; ciclo de dependência.

**Onde vai um código novo?** Ele vai para `libs/` quando responde "sim" às quatro perguntas da
[ADR-0027](kb/decisoes/0027-estrutura-apps-products-libs.md):

1. a API não carrega vocabulário de um produto ou de um cliente;
2. outro produto usaria;
3. dá para testar sozinho;
4. tem dono.

Entre os tipos de lib:

- **integration** fala com UM sistema externo e não sabe o que é regra de negócio;
- **capability** é mecanismo técnico reutilizável (gerar PDF, exportar planilha) sem estado de
  negócio;
- **domain** é um bounded context: as entidades, as regras e os casos de uso de um assunto do
  negócio (catálogo, carrinho, pedido), com as portas e os adapters dele;
- **platform** é o que todo app usa (ler ambiente, publicar evento, medir). Cuidado com o "é
  genérico, vai para a platform": é assim que uma lib vira depósito.

O que precisa de **dois ou mais domínios** não é de nenhum deles: é do **produto**.

## 4. Dentro de uma unidade: Ports & Adapters

`domain` e `product` têm camadas, de cima para baixo:

```text
adapters/      fala com o mundo: Postgres, Redis, disco, HTTP, e-mail
application/   os casos de uso: orquestram portas, não sabem de onde o dado vem
ports/         os contratos (Protocol) que a application usa
domain/        a regra pura: entidades, objetos de valor, erros
```

- Uma camada só importa as de baixo (contrato `camadas` no `.importlinter`).
- Integração com I/O só entra pela camada `adapters/`; a `application/` e os `ports/` podem usar
  só os `pure_modules` dela.
- A porta é de quem a usa: o domínio declara a porta, o adapter a implementa. A plataforma declara
  as portas que são de todo app (`EventPublisher`, `MetricsPublisher`), e as integrações
  `messaging` e `prometheus` as implementam.
- Os adapters ficam em subpastas por tecnologia: `adapters/postgres/`, `adapters/redis/`,
  `adapters/llm/`. O adapter de desenvolvimento (fake, log, disco local) mora na mesma camada.
- Cada domínio que escolhe adapter por configuração tem uma **factory** em `adapters/`
  (`build_llm_provider`, `build_payment_gateway`), que recebe um objeto de configuração tipado.
  Ela não lê o ambiente.

## 5. O produto

O produto `ecommerce` guarda o que cruza domínios. Hoje, em `application/`:

```text
stock              publica `stock.low` e dá baixa no estoque de um pedido pago
catalog_indexing   lê o catálogo e indexa para o assistente de IA
event_handlers     o que fazer com cada evento consumido pelo event-worker
seed               o seed semântico de catálogo, estoque e configuração
```

Fora do pacote, na pasta do produto: `contracts/api/` (os contratos OpenAPI) e `migrations/` (o
histórico Alembic do banco da loja). O banco é um só: cada domínio declara as tabelas dele em
`adapters/postgres/`, e `revold_ecommerce.adapters.database` junta todas no `metadata` que o
Alembic compara com o banco.

## 6. O app (composition root)

O app é o único lugar que lê o ambiente, escolhe os adapters e monta tudo. Em cada app Python,
`settings.py` é o único módulo que lê variável de ambiente, pelo `revold_platform.configuration`.
No `api-gateway`, `dependencies.py` monta os adapters e `routers/` expõe as rotas; nos workers,
`celery_app.py` registra as tarefas e chama os casos de uso do produto.

O app não é verificado pelo import-linter: ele existe para importar tudo. Por isso há um teste de
arquitetura só para ele: o app importa apenas o que declara em `depends_on`, e nunca outro app.

Os sites (`storefront`, `admin-dashboard`) são apps TypeScript. Não importam pacote Python: falam
com o `api-gateway` por HTTP.

## 7. Quem fiscaliza

| Regra | Ferramenta | Onde roda |
|---|---|---|
| tipo e `depends_on` (D1), ciclo, `pyproject.toml` coerente com o manifesto | `tooling` (`dev check`) | hook e CI |
| versão que não subiu | `tooling` (`dev check`) | hook e CI |
| importação entre unidades e camadas | `.importlinter` gerado (`dev lint-imports`) | hook e CI |
| tipos | mypy (`dev check`) | hook de pre-push e CI |
| arquivos gerados em dia | `dev check` e `tests/architecture/` | hook e CI |
| ambiente lido só no `settings.py` do app | `tests/architecture/test_units.py` | pytest |
| app importa só o que declara, e nunca outro app | `tests/architecture/test_app_imports.py` | pytest |
| todo job do CI está ligado ao `CI OK` | `tests/architecture/test_ci_workflow.py` | pytest |
| rota da API e contrato OpenAPI batem (método e caminho) | `api-gateway/tests/test_contract_routes.py` | pytest |
| as migrações constroem exatamente o que os modelos descrevem | `products/ecommerce/tests/test_migrations_match_models.py` | pytest com Postgres (CI) |
| a imagem do app leva tudo o que ele importa | job "Imagem" | CI |
| o cliente consegue comprar (carrinho, checkout, busca) | job "E2E (Playwright)" | CI |

O hook e o CI rodam o mesmo `dev check`, de propósito.

## 8. Criar uma unidade nova

```bash
uv run dev new <kind> <id> --depends-on <ids> --dry-run   # mostra os arquivos
uv run dev new <kind> <id> --depends-on <ids>             # cria
uv run dev new app <produto>/<app> --runtime fastapi-api  # app: fastapi-api ou celery-worker
uv run dev check
```

Os modelos estão em `tooling/templates/` (`python-lib`, `fastapi-api`, `celery-worker`). A unidade
nasce com o nome `revold_<nome>` (o app, sem prefixo), `lifecycle: pilot`, testes e README. O
`dev new` já regenera o `.importlinter` e o CODEOWNERS. Detalhe dos casos (domínio novo, integração
nova, produto novo, promover para `libs/`) na seção 10 da
[aula](onboarding/arquitetura-monorepo.md).

## 9. Para onde isto pode ir

Hoje o repositório é um monolito modular: unidades isoladas por fronteira de código, com três
processos Python (a API e dois workers) que compartilham as libs. As portas já separam quem chama de
quem implementa, e o app já isola "montar" de "a lógica". Extrair um domínio como serviço próprio é
uma opção, exercida caso a caso quando houver motivo concreto (escala, time dono, cadência de
deploy), e não uma meta.
