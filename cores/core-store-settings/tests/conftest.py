from __future__ import annotations

import pytest

from core_store_settings.domain import StoreSettings


class FakeStoreSettingsRepository:
    """Adapter fake em memória, mesma forma da porta StoreSettingsRepository,
    só para teste."""

    def __init__(self) -> None:
        self._settings: StoreSettings | None = None

    async def get(self) -> StoreSettings | None:
        return self._settings

    async def save(self, settings: StoreSettings) -> None:
        self._settings = settings


@pytest.fixture
def fake_repository() -> FakeStoreSettingsRepository:
    return FakeStoreSettingsRepository()
