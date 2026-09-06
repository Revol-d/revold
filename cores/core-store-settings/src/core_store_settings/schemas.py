"""Schemas Pydantic que espelham contracts/api/store-settings.yaml."""
from __future__ import annotations

from pydantic import BaseModel


class StoreSettingsSchema(BaseModel):
    cnpj: str
    store_name: str
    contact_email: str
    contact_phone: str
    store_address: str
    low_stock_threshold: int


class UpdateStoreSettingsRequestSchema(BaseModel):
    cnpj: str | None = None
    store_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    store_address: str | None = None
    low_stock_threshold: int | None = None
