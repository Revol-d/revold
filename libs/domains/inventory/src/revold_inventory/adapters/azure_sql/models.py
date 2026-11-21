"""Modelo SQLAlchemy do estoque no Azure SQL. Vive só no adapter -- revold_inventory
não o conhece.

Espelha adapters/postgres/models.py: mesma tabela, mesmos tipos portáveis (String/Integer).
"""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from revold_azure_sql.db import Base


class StockLevelModel(Base):
    __tablename__ = "inventory_stock_levels"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
