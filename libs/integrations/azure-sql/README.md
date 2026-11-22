# `revold_azure_sql`

Cliente do Azure SQL Database: engine, fábrica de sessão e a base declarativa do SQLAlchemy.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

`make_engine(database_url)`, `make_session_factory(engine)`, `get_session` e `Base`, a base
declarativa de onde os modelos Azure SQL dos domínios herdam (lida por
`products/ecommerce/migrations_azure_sql/`). Única integração de persistência do repositório
([ADR-0032](../../../docs/kb/decisoes/0032-migracao-postgres-para-azure-sql.md) — Postgres foi
removido).

Usa `aioodbc` (driver assíncrono) + ODBC Driver 17/18 for SQL Server instalado na máquina —
não é instalado pelo `uv sync`, é um componente de sistema operacional. Ver
[docs/guides/azure-setup.md](../../../docs/guides/azure-setup.md) ou a documentação da Microsoft
para instalar.

## O que NÃO faz

- **Não conhece tabela nem domínio.** Modelos e repositórios moram em `adapters/azure_sql/` do
  domínio dono da porta.
- **Não lê `DATABASE_URL`.** Quem lê é o `settings.py` do app.

## Testes

```powershell
uv run pytest libs/integrations/azure-sql/tests -q
```
