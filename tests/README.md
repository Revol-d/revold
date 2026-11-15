# `tests/` — a suíte central

O teste de uma unidade mora **dentro da unidade** (`libs/.../tests/`, `products/.../tests/`,
`apps/.../tests/`). Esta pasta guarda só o que é do repositório inteiro.

| Pasta | O que tem |
|---|---|
| `architecture/` | os gates de arquitetura que rodam no pytest: gerados em dia, contratos presentes, ambiente lido só no `settings.py`, app que importa só o que declara, todo job do CI ligado ao `CI OK` |
| `support/revold_testing/` | as fábricas de dados compartilhadas (Factory Boy e Faker, [ADR-0012](../docs/kb/decisoes/0012-estrategia-de-testes-dados-realistas-e-evals.md)), um módulo por domínio |

`support/` não é unidade: é código de teste, importável pelos testes por causa do `pythonpath` do
`pyproject.toml` da raiz. Por isso pode conhecer vários domínios sem quebrar a regra de dependência.
Nada de produção importa `revold_testing`.

```powershell
uv run pytest tests/architecture -q
```

Mudança nesta pasta conta como global no cálculo de afetados: o CI roda todos os testes.
