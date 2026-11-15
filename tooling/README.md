# `tooling` — a ferramenta de desenvolvimento do monorepo

`uv run dev <comando>`. Decisão: [ADR-0030](../docs/kb/decisoes/0030-tooling-proprio-e-manifesto-unit-yaml.md).

| Comando | O que faz |
|---|---|
| `dev check [--no-mypy]` | o gate único: manifesto, gerados em dia, versões, import-linter e mypy |
| `dev gen` | regenera `.importlinter` e `.github/CODEOWNERS` a partir dos `unit.yaml` |
| `dev lint-imports` | só o import-linter |
| `dev affected [--base REF] [--json]` | as unidades que a branch afeta, e os consumidores delas |
| `dev test [--affected]` | os testes: todos, ou só os das unidades afetadas. O que vier depois vai para o pytest |
| `dev new <kind> <id>` | cria uma unidade a partir de `templates/` |
| `dev version` | a versão de cada unidade Python |
| `dev bump <unidade> <parte>` | sobe a versão de **uma** unidade e atualiza o `uv.lock` |
| `dev build <app> [--image]` | o BOM do fecho em `dist/<app>/`; com `--image`, a imagem Docker |
| `dev build <unidade>...` | o wheel de uma unidade solta, em `dist/` |
| `dev release <app> <parte> [--dry-run]` | testa o fecho, sobe o app e grava o BOM em `.releases/` |
| `dev verify-release <app>` | confere o BOM gravado contra o código (o `release.yml` usa) |

## O que faz

- **Manifesto**: lê e valida os `unit.yaml` contra [schema/unit.schema.json](schema/unit.schema.json)
  e contra as regras que o schema não alcança: ids únicos, `depends_on` existente, grafo sem ciclo,
  regra de dependência entre tipos (D1), `production` sem depender de `prototype`,
  `pyproject.toml` coerente com o `depends_on` e toda unidade resolvida do workspace (nunca do
  PyPI).
- **Gerados** (`dev gen`): `.importlinter` e `.github/CODEOWNERS`. Nunca se editam à mão; o
  `dev check` reprova quando o commitado diverge do gerado.
- **Gate único** (`dev check`): o mesmo comando no hook e no CI.
- **Afetados** (`dev affected`, `dev test --affected`): arquivos alterados → unidades →
  consumidores. Caminho global (`uv.lock`, `tooling/`, `tests/`, `deploy/`) afeta todas.
- **Unidade nova** (`dev new`): valida o id antes de escrever, compila o gerado e revalida o
  manifesto; se algo falhar, desfaz tudo. App aceita `<produto>/<app>` e
  `--runtime fastapi-api|celery-worker`; `--dry-run` só lista. App Python entra pelo caminho nos
  `members` do workspace, porque o glob `apps/*` exigiria `pyproject.toml` em `apps/<produto>/`.
- **Versão e release** (`dev version`, `dev bump`, `dev build`, `dev release`,
  `dev verify-release`): ver [docs/versionamento-e-deploy.md](../docs/versionamento-e-deploy.md).
- **Gate de versão** (dentro do `dev check`): o `src/` de uma unidade mudou desde o último release
  de um app que a usa, e a versão não subiu? Falha. Compara o sha256 do `src/` com o BOM em
  `.releases/<app>.json`; não depende do histórico do git. App sem release é pulado, e o gate diz
  que pulou.

Configuração que não pertence a nenhuma unidade (donos padrão e da plataforma, caminhos globais do
cálculo de afetados): [repo.yaml](repo.yaml).

## Os modelos do `dev new`

| Modelo | Para | O que nasce |
|---|---|---|
| [templates/python-lib](templates/python-lib/) | `integration`, `capability`, `domain`, `product` | `unit.yaml`, `pyproject.toml`, `README.md`, o pacote e um teste da API pública. Domínio e produto nascem com as camadas |
| [templates/fastapi-api](templates/fastapi-api/) | `app --runtime fastapi-api` | app factory, `/health`, `/ready`, `settings.py`, log com correlation id, teste de fumaça e `Dockerfile` |
| [templates/celery-worker](templates/celery-worker/) | `app --runtime celery-worker` | o app Celery, `settings.py`, uma tarefa de exemplo e teste de fumaça |

Não há modelo de site (`next-web`): copie um dos sites existentes e escreva o `unit.yaml`.

## O que NÃO faz

- Não publica nada: a tag `<app>@<versão>`, o GitHub Release e a imagem são do `release.yml`.
- Não roda o ruff: ele é chamado direto (`uv run ruff check .`), no hook e no job de lint do CI.
- Não cobre os sites no release: o BOM e o `dev release` são só para app Python.
- Não entra em imagem nenhuma: é ferramenta de desenvolvimento, fora de `libs/` e `products/`.

## Testes

```powershell
uv run pytest tooling/tests -q
```

Os testes montam um monorepo de mentira numa pasta temporária, para o tooling ler e escrever sem
tocar no de verdade. Os de `affected` e de fecho rodam sobre o manifesto real.
