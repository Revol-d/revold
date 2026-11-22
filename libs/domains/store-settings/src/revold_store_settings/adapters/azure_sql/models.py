"""Modelo SQLAlchemy da configuração da loja no Azure SQL. Vive só no adapter —
revold_store_settings não o conhece (ADR-0002, ADR-0019).

Espelha libs/domains/store-settings/src/revold_store_settings/adapters/postgres/models.py:
mesma tabela — só troca o `Base` de origem (revold_azure_sql em vez de revold_postgres),
porque as duas não podem registrar a mesma tabela no mesmo `Base.metadata` no mesmo
processo (ver `products/ecommerce/src/revold_ecommerce/adapters/database.py`).

`String` NÃO é portável para texto livre aqui: no dialeto mssql vira `VARCHAR`, sujeito à
colação do servidor (`SQL_Latin1_General_CP1_CI_AS` por padrão) -- caracteres fora do
CP1252 (emoji, a maior parte do CJK, etc.) são trocados por `?` ao gravar, SEM erro
nenhum (achado de revisão, confirmado contra um SQL Server 2025 real). `store_name` e
`store_address` são texto livre digitado pelo lojista, então usam `Unicode` (`NVARCHAR`),
que preserva qualquer caractere. `id`/`cnpj`/`contact_email`/`contact_phone` continuam
`String`: são valores estruturados/ASCII por contrato (ADR-0002), não texto livre.

Só existe um registro (id fixo "default") — não há múltiplas lojas hoje.
"""
from __future__ import annotations

from sqlalchemy import Integer, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from revold_azure_sql.db import Base

SINGLETON_ID = "default"


class StoreSettingsModel(Base):
    __tablename__ = "store_settings"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=SINGLETON_ID)
    cnpj: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    store_name: Mapped[str] = mapped_column(Unicode(200), nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    store_address: Mapped[str] = mapped_column(Unicode(500), nullable=False, default="")
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
