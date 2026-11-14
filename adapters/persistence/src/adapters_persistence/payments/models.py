"""Modelo SQLAlchemy de cobrança de pagamento. Vive só no adapter —
core_payments não o conhece (ADR-0002, ADR-0024)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from adapters_persistence.db import Base


class ChargeModel(Base):
    __tablename__ = "payment_charges"

    charge_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_charge_id: Mapped[str] = mapped_column(String(120), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    pix_qr_code: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    pix_copy_paste: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
