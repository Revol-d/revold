"""Modelo SQLAlchemy do estoque. Vive só no adapter — core_inventory não o conhece."""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from adapters_persistence.db import Base


class StockLevelModel(Base):
    __tablename__ = "inventory_stock_levels"

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
