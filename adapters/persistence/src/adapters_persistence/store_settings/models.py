"""Modelo SQLAlchemy da configuração da loja. Vive só no adapter —
core_store_settings não o conhece (ADR-0002, ADR-0019).

Só existe um registro (id fixo "default") — não há múltiplas lojas hoje.
"""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from adapters_persistence.db import Base

SINGLETON_ID = "default"


class StoreSettingsModel(Base):
    __tablename__ = "store_settings"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=SINGLETON_ID)
    cnpj: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    store_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    store_address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
