"""O esquema do banco da loja: os modelos de todos os domínios que guardam dado
persistente, contra o Azure SQL Database (ver o plano de migração Postgres -> Azure
SQL, docs internos -- Fase 7, corte concluído: Postgres removido).

Quem usa:

- o `env.py` de `products/ecommerce/migrations_azure_sql/`, para o
  `alembic revision --autogenerate` enxergar as tabelas;
- o teste `tests/test_migrations_match_models.py`, que reprova quando os modelos e
  as migrações divergem.

Domínio novo com tabela entra na lista abaixo, no mesmo PR da migração.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import MetaData

# Importados só para registrar as tabelas no `Base.metadata`.
from revold_ai_assistant.adapters.azure_sql import models as _ai_assistant  # noqa: F401
from revold_ai_assistant.adapters.azure_sql.vector_type import Vector
from revold_azure_sql.db import Base
from revold_catalog.adapters.azure_sql import models as _catalog  # noqa: F401
from revold_identity.adapters.azure_sql import api_key_models as _identity  # noqa: F401
from revold_inventory.adapters.azure_sql import models as _inventory  # noqa: F401
from revold_orders.adapters.azure_sql import models as _orders  # noqa: F401
from revold_payments.adapters.azure_sql import models as _payments  # noqa: F401
from revold_store_settings.adapters.azure_sql import models as _store_settings  # noqa: F401

metadata: MetaData = Base.metadata


def compare_type(
    context: Any, inspected_column: Any, metadata_column: Any, inspected_type: Any, metadata_type: Any
) -> bool | None:
    """Comparador de tipo do Alembic (ver `:ref:compare_types` da doc do Alembic) --
    sem isto, toda coluna `Vector` (ai-assistant) aparece como "mudou" em
    `test_migrations_match_models.py`/`alembic revision --autogenerate`: o dialeto
    mssql reflete `VECTOR(n)` como `VARBINARY(n*4+8)` (não reconhece o tipo nativo),
    e o comparador padrão do Alembic não sabe que isso é o mesmo `Vector(n)` do
    modelo. Confirmado rodando contra um SQL Server real: sem este comparador, a
    diferença aparece como `modify_type ... VARBINARY(6152) -> Vector(1536)` mesmo
    sem nenhuma mudança de verdade.
    """
    if isinstance(metadata_type, Vector):
        return False
    return None


__all__ = ["metadata", "compare_type"]
