"""Schemas Pydantic que espelham contracts/api/cart.yaml."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemSchema(BaseModel):
    sku: str
    name: str
    variant_label: str
    unit_price: Decimal
    quantity: int = Field(ge=1)


class CartSchema(BaseModel):
    cart_id: str
    items: list[CartItemSchema]
    total: Decimal
    currency: str = "BRL"


class AddItemRequestSchema(BaseModel):
    sku: str
    name: str
    variant_label: str
    unit_price: Decimal
    quantity: int = Field(default=1, ge=1)


class UpdateQuantityRequestSchema(BaseModel):
    quantity: int = Field(ge=1)


class CheckoutHandoffResponseSchema(BaseModel):
    handoff_url: str
    provider: str
