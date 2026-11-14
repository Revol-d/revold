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
    available_quantity: int | None = Field(
        default=None,
        description=(
            "Quantidade disponível em core-inventory no momento da consulta, "
            "ou null se o SKU ainda não tem estoque cadastrado. Informativo "
            "apenas — não bloqueia adicionar ao carrinho; a reserva de "
            "verdade só acontece no checkout."
        ),
    )


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
    order_id: str
