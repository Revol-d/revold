"""Schemas Pydantic que espelham products/ecommerce/contracts/api/orders.yaml."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class OrderLineSchema(BaseModel):
    sku: str
    product_name: str
    variant_label: str
    unit_price: Decimal
    quantity: int = Field(ge=1)
    subtotal: Decimal


class OrderSchema(BaseModel):
    order_id: str
    cart_id: str
    lines: list[OrderLineSchema]
    total: Decimal
    currency: str = "BRL"
    payment_status: str
    fulfillment_status: str
    created_at: str


class OrderPageSchema(BaseModel):
    items: list[OrderSchema]
    page: int
    page_size: int
    total: int


class UpdatePaymentStatusRequestSchema(BaseModel):
    action: Literal["mark_paid", "cancel"]


class UpdateFulfillmentStatusRequestSchema(BaseModel):
    action: Literal["mark_shipped", "mark_delivered"]
