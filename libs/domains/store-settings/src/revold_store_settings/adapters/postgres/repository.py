"""Implementação Postgres da porta revold_store_settings.ports.StoreSettingsRepository
(ADR-0019)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_store_settings.adapters.postgres.models import SINGLETON_ID, StoreSettingsModel
from revold_store_settings.domain import StoreSettings


def _to_domain(model: StoreSettingsModel) -> StoreSettings:
    return StoreSettings(
        cnpj=model.cnpj,
        store_name=model.store_name,
        contact_email=model.contact_email,
        contact_phone=model.contact_phone,
        store_address=model.store_address,
        low_stock_threshold=model.low_stock_threshold,
    )


class PostgresStoreSettingsRepository:
    """Implementa revold_store_settings.ports.StoreSettingsRepository via
    SQLAlchemy async. Só existe um registro (id fixo, ver
    revold_store_settings.adapters.postgres.models.SINGLETON_ID) — save() faz
    upsert nele."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> StoreSettings | None:
        model = await self._session.get(StoreSettingsModel, SINGLETON_ID)
        if model is None:
            return None
        return _to_domain(model)

    async def save(self, settings: StoreSettings) -> None:
        model = await self._session.get(StoreSettingsModel, SINGLETON_ID)
        if model is None:
            model = StoreSettingsModel(id=SINGLETON_ID)
            self._session.add(model)
        model.cnpj = settings.cnpj
        model.store_name = settings.store_name
        model.contact_email = settings.contact_email
        model.contact_phone = settings.contact_phone
        model.store_address = settings.store_address
        model.low_stock_threshold = settings.low_stock_threshold
        await self._session.commit()
