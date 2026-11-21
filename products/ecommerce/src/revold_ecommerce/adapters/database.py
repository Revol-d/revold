"""O esquema do banco da loja: os modelos de todos os domínios que guardam dado persistente.

O banco é um só para a loja. Hoje, durante a migração Postgres -> Azure SQL (ver o plano em
docs internos), existem DOIS históricos de migração em paralelo:
`products/ecommerce/migrations/` (Postgres, o de sempre) e
`products/ecommerce/migrations_azure_sql/` (Azure SQL, novo). Cada um lê a metadata do
provider certo via `get_metadata(provider)`.

Por que duas metadatas e não uma só: os modelos `adapters/postgres/models.py` e
`adapters/azure_sql/models.py` de um mesmo domínio são classes SQLAlchemy DIFERENTES (tipos de
coluna podem divergir entre dialetos) mapeando a MESMA tabela — duas classes não podem
registrar a mesma tabela no mesmo `Base.metadata` no mesmo processo. Por isso cada dialeto tem
o próprio `Base` (`revold_postgres.db.Base` / `revold_azure_sql.db.Base`) e a própria metadata.

Quem usa:

- o `env.py` de cada histórico de migração, para o `alembic revision --autogenerate` enxergar
  as tabelas do dialeto certo;
- o teste `tests/test_migrations_match_models.py`, que reprova quando os modelos e as migrações
  divergem (hoje só cobre o Postgres — ver nota lá).

Domínio novo com tabela entra na lista do dialeto certo abaixo, no mesmo PR da migração.
Domínio ainda não migrado para Azure SQL (a maioria, enquanto a troca está em andamento) só
aparece na lista do Postgres.
"""

from __future__ import annotations

from sqlalchemy import MetaData


def _postgres_metadata() -> MetaData:
    # Importados só para registrar as tabelas no `Base.metadata` do Postgres.
    from revold_ai_assistant.adapters.postgres import models as _ai_assistant  # noqa: F401
    from revold_catalog.adapters.postgres import models as _catalog  # noqa: F401
    from revold_identity.adapters.postgres import api_key_models as _identity  # noqa: F401
    from revold_inventory.adapters.postgres import models as _inventory  # noqa: F401
    from revold_orders.adapters.postgres import models as _orders  # noqa: F401
    from revold_payments.adapters.postgres import models as _payments  # noqa: F401
    from revold_postgres.db import Base
    from revold_store_settings.adapters.postgres import models as _store_settings  # noqa: F401

    return Base.metadata


def _azure_sql_metadata() -> MetaData:
    # Importados só para registrar as tabelas no `Base.metadata` do Azure SQL. Só os domínios
    # já migrados entram aqui -- a lista cresce fase a fase (ver o plano de migração).
    from revold_azure_sql.db import Base
    from revold_inventory.adapters.azure_sql import models as _inventory  # noqa: F401
    from revold_orders.adapters.azure_sql import models as _orders  # noqa: F401
    from revold_payments.adapters.azure_sql import models as _payments  # noqa: F401
    from revold_store_settings.adapters.azure_sql import models as _store_settings  # noqa: F401

    return Base.metadata


def get_metadata(provider: str) -> MetaData:
    if provider == "postgres":
        return _postgres_metadata()
    if provider == "azure-sql":
        return _azure_sql_metadata()
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")


# Compatibilidade: todo código existente (env.py do Postgres, o teste de migrações) importa
# `metadata` direto, sem saber de providers. Continua sendo a metadata do Postgres.
metadata: MetaData = get_metadata("postgres")

__all__ = ["metadata", "get_metadata"]
