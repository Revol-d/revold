"""O esquema do banco da loja: os modelos de todos os domínios que guardam dado no Postgres.

O banco é um só para a loja, e o histórico dele (`products/ecommerce/migrations/`) é do produto.
Cada domínio declara as próprias tabelas na camada `adapters/postgres/`; este módulo só junta
todas no mesmo `metadata`, que é o que o Alembic compara com o banco.

Quem usa:

- o `env.py` das migrações, para o `alembic revision --autogenerate` enxergar todas as tabelas;
- o teste `tests/test_migrations_match_models.py`, que reprova quando os modelos e as migrações
  divergem.

Domínio novo com tabela no Postgres entra na lista abaixo, no mesmo PR da migração.
"""

from __future__ import annotations

from sqlalchemy import MetaData

# Importados só para registrar as tabelas no `Base.metadata`.
from revold_ai_assistant.adapters.postgres import models as _ai_assistant  # noqa: F401
from revold_catalog.adapters.postgres import models as _catalog  # noqa: F401
from revold_identity.adapters.postgres import api_key_models as _identity  # noqa: F401
from revold_inventory.adapters.postgres import models as _inventory  # noqa: F401
from revold_orders.adapters.postgres import models as _orders  # noqa: F401
from revold_payments.adapters.postgres import models as _payments  # noqa: F401
from revold_postgres.db import Base
from revold_store_settings.adapters.postgres import models as _store_settings  # noqa: F401

metadata: MetaData = Base.metadata

__all__ = ["metadata"]
