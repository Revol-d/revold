"""Schemas Pydantic que espelham products/ecommerce/contracts/api/catalog.yaml.

Mantidos manualmente em sincronia com o contrato por enquanto; um gerador
(openapi-python-client ou datamodel-code-generator) pode substituir isso
depois, mas o contrato YAML continua sendo a fonte da verdade.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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


class CreateCategoryRequestSchema(BaseModel):
    slug: str
    name: str


class CreateProductVariantSchema(BaseModel):
    sku: str
    size: str
    color: str
    in_stock: bool = True


class CreateProductRequestSchema(BaseModel):
    sku: str
    name: str
    category_slug: str
    price: MoneySchema
    description: str = ""
    images: list[str] = Field(default_factory=list)
    original_price: MoneySchema | None = None
    variants: list[CreateProductVariantSchema] = Field(default_factory=list)


class UpdateProductRequestSchema(BaseModel):
    """Todo campo é opcional: só o que for enviado é alterado. Não mexe nas
    variantes (ver POST /products/{sku}/variants para isso)."""

    name: str | None = None
    category_slug: str | None = None
    price: MoneySchema | None = None
    description: str | None = None
    images: list[str] | None = None
    original_price: MoneySchema | None = None
    clear_original_price: bool = False


class UpdateProductVariantRequestSchema(BaseModel):
    """Todo campo é opcional: só o que for enviado é alterado. O SKU da
    variante nunca muda por aqui (ver revold_catalog.application.use_cases.UpdateProductVariant)."""

    size: str | None = None
    color: str | None = None
    in_stock: bool | None = None
