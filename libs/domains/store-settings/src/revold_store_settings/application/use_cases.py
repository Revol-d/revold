"""Casos de uso do `store-settings` (ADR-0019)."""
from __future__ import annotations

from revold_store_settings.domain import StoreSettings
from revold_store_settings.ports import StoreSettingsRepository


class GetStoreSettings:
    """Lê a configuração atual da loja. Se a Nick ainda não configurou
    nada, devolve um registro vazio (todo campo textual em branco) usando
    `default_low_stock_threshold` como limiar — o mesmo valor que
    LOW_STOCK_THRESHOLD (env var) usava antes deste core existir, para não
    mudar o comportamento de quem nunca abriu a tela de configurações."""

    def __init__(self, repository: StoreSettingsRepository) -> None:
        self._repository = repository

    async def execute(self, *, default_low_stock_threshold: int) -> StoreSettings:
        settings = await self._repository.get()
        if settings is not None:
            return settings
        return StoreSettings(
            cnpj="",
            store_name="",
            contact_email="",
            contact_phone="",
            store_address="",
            low_stock_threshold=default_low_stock_threshold,
        )


class UpdateStoreSettings:
    """Atualiza os campos informados (não-None) da configuração da loja,
    preservando os demais — mesmo padrão de UpdateProduct em `catalog`:
    todos os campos são opcionais, só o que for passado é alterado."""

    def __init__(self, repository: StoreSettingsRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        default_low_stock_threshold: int,
        cnpj: str | None = None,
        store_name: str | None = None,
        contact_email: str | None = None,
        contact_phone: str | None = None,
        store_address: str | None = None,
        low_stock_threshold: int | None = None,
    ) -> StoreSettings:
        current = await GetStoreSettings(self._repository).execute(
            default_low_stock_threshold=default_low_stock_threshold
        )
        updated = StoreSettings(
            cnpj=cnpj if cnpj is not None else current.cnpj,
            store_name=store_name if store_name is not None else current.store_name,
            contact_email=contact_email if contact_email is not None else current.contact_email,
            contact_phone=contact_phone if contact_phone is not None else current.contact_phone,
            store_address=store_address if store_address is not None else current.store_address,
            low_stock_threshold=(
                low_stock_threshold if low_stock_threshold is not None else current.low_stock_threshold
            ),
        )
        await self._repository.save(updated)
        return updated
