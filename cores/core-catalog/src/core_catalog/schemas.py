"""Schemas Pydantic que espelham contracts/api/catalog.yaml.

Mantidos manualmente em sincronia com o contrato por enquanto; um gerador
(openapi-python-client ou datamodel-code-generator) pode substituir isso
depois, mas o contrato YAML continua sendo a fonte da verdade.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MoneySchema(BaseModel):
    amount: Decimal
    currency: str = "BRL"


class CategorySchema(BaseModel):
    slug: str
    name: str


class ProductVariantSchema(BaseModel):
    sku: str
    size: str
    color: str
    in_stock: bool


class ProductSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    name: str
    description: str = ""
    category: CategorySchema
    price: MoneySchema
    original_price: MoneySchema | None = None
    variants: list[ProductVariantSchema]
    images: list[str]


class ProductPageSchema(BaseModel):
    items: list[ProductSchema]
    page: int
    page_size: int
    total: int
