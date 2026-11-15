# `revold_postgres`

Cliente do Postgres: engine, fábrica de sessão e a base declarativa do SQLAlchemy.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

`make_engine(database_url)`, `make_session_factory(engine)`, `get_session` e `Base`, a base declarativa de onde os modelos de todos os domínios herdam (é ela que o Alembic lê em `products/ecommerce/migrations/`).

## O que NÃO faz

- **Não conhece tabela nem domínio.** Modelos e repositórios moram em `adapters/postgres/` do domínio dono da porta.
- **Não lê `DATABASE_URL`.** Quem lê é o `settings.py` do app.

## Testes

```powershell
uv run pytest libs/integrations/postgres/tests -q
```
