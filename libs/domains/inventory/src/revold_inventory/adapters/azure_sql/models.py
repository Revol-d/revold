"""Modelo SQLAlchemy do estoque no Azure SQL. Vive só no adapter -- revold_inventory
não o conhece.

Espelha adapters/postgres/models.py: mesma tabela. A exceção é `sku`, que não pode usar
`String` puro: no dialeto mssql ele vira `VARCHAR` com a colação padrão do servidor
(`SQL_Latin1_General_CP1_CI_AS`), que ignora maiúsculas e troca caracteres fora do CP1252
por `?`. Como `sku` é a chave, SKUs diferentes passariam a dividir a mesma linha de estoque,
sem erro. `NVARCHAR` com colação binária compara o valor exato, como o Postgres faz.
"""
from __future__ import annotations

from sqlalchemy import Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from revold_azure_sql.db import Base

SKU_COLLATION = "Latin1_General_100_BIN2"


class StockLevelModel(Base):
    __tablename__ = "inventory_stock_levels"

    sku: Mapped[str] = mapped_column(Unicode(64, collation=SKU_COLLATION), primary_key=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
