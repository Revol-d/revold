"""Porta (interface) que `store-settings` espera que a infraestrutura
implemente. Qualquer adapter (Postgres, um fake em memória para teste)
implementa este Protocol — `store-settings` nunca importa SQLAlchemy.
"""
from __future__ import annotations

from typing import Protocol

from revold_store_settings.domain import StoreSettings


class StoreSettingsRepository(Protocol):
    async def get(self) -> StoreSettings | None:
        """Devolve o registro de configuração atual, ou None se a Nick
        ainda não configurou nada (loja recém-criada)."""
        ...

    async def save(self, settings: StoreSettings) -> None:
        """Substitui o registro de configuração por completo (upsert —
        só existe um registro, ver ADR-0019)."""
        ...
