"""Schemas Pydantic que espelham contracts/api/payments.yaml."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CreateChargeRequestSchema(BaseModel):
    method: Literal["pix", "credit_card"]


class ChargeSchema(BaseModel):
    charge_id: str
    order_id: str
    provider: str
    method: str
    amount: Decimal
    currency: str
    status: str
    pix_qr_code: str | None = None
    pix_copy_paste: str | None = None
    checkout_url: str | None = None
    created_at: str
