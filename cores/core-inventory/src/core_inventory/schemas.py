"""Schemas Pydantic que espelham contracts/api/inventory.yaml.

Mantidos manualmente em sincronia com o contrato por enquanto; um gerador
(openapi-python-client ou datamodel-code-generator) pode substituir isso
depois, mas o contrato YAML continua sendo a fonte da verdade.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class StockLevelSchema(BaseModel):
    sku: str
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int


class ReserveStockRequestSchema(BaseModel):
    quantity: int = Field(gt=0)


class ReleaseStockRequestSchema(BaseModel):
    quantity: int = Field(gt=0)


class ReceiveStockRequestSchema(BaseModel):
    quantity: int = Field(gt=0)
