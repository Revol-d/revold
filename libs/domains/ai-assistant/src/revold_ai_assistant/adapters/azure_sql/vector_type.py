"""Tipo SQLAlchemy customizado pro `VECTOR(n)` nativo do Azure SQL Database
(GA desde meados de 2025, verificado funcionando com DiskANN na Fase 0 do plano
de migração Postgres -> Azure SQL, docs internos).

O SQLAlchemy (ainda, nesta versão) não tem suporte nativo a este tipo pro
dialeto mssql -- diferente do pgvector.sqlalchemy.Vector usado no adapter
Postgres, que é uma lib de terceiro já pronta. Testado e confirmado via
Azure SQL real (não assumido): insert/select via bind parameter funcionam
normalmente com este tipo, sem a restrição que o CONTAINSTABLE tem (ver
adapters/azure_sql/repository.py do catalog) -- VECTOR_DISTANCE aceita
parâmetro bindado no segundo argumento sem problema.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[list[float]]):
    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: Any) -> str:
        return f"VECTOR({self.dim})"

    def bind_processor(self, dialect: Dialect) -> Callable[[list[float] | None], str | None]:
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return json.dumps([float(x) for x in value])

        return process

    def result_processor(
        self, dialect: Dialect, coltype: Any
    ) -> Callable[[str | None], list[float] | None]:
        def process(value: str | None) -> list[float] | None:
            if value is None:
                return None
            return json.loads(value) if isinstance(value, str) else value

        return process
