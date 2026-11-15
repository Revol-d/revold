"""Router HTTP do `store-settings` (ADR-0019). Fino: só traduz HTTP <->
caso de uso — exatamente o mesmo padrão de inventory.py/identity.py."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api_gateway.dependencies import (
    get_low_stock_threshold_env_default,
    get_store_settings_repository,
)
from api_gateway.security import require_any_role
from revold_identity.domain import AuthenticatedUser, Role
from revold_store_settings.domain import StoreSettings
from revold_store_settings.ports import StoreSettingsRepository
from revold_store_settings.application.schemas import StoreSettingsSchema, UpdateStoreSettingsRequestSchema
from revold_store_settings.application.use_cases import GetStoreSettings, UpdateStoreSettings

router = APIRouter(prefix="/api/store-settings", tags=["store-settings"])


def _to_schema(settings: StoreSettings) -> StoreSettingsSchema:
    return StoreSettingsSchema(
        cnpj=settings.cnpj,
        store_name=settings.store_name,
        contact_email=settings.contact_email,
        contact_phone=settings.contact_phone,
        store_address=settings.store_address,
        low_stock_threshold=settings.low_stock_threshold,
    )


@router.get("", response_model=StoreSettingsSchema)
async def get_store_settings(
    repository: StoreSettingsRepository = Depends(get_store_settings_repository),
    _admin: AuthenticatedUser = Depends(require_any_role(Role.ADMIN)),
) -> StoreSettingsSchema:
    """Só ADMIN (ADR-0019) — CNPJ e contato são dado administrativo da
    empresa, mais sensível que o catálogo/estoque (STAFF+ADMIN)."""
    settings = await GetStoreSettings(repository).execute(
        default_low_stock_threshold=get_low_stock_threshold_env_default()
    )
    return _to_schema(settings)


@router.put("", response_model=StoreSettingsSchema)
async def update_store_settings(
    body: UpdateStoreSettingsRequestSchema,
    repository: StoreSettingsRepository = Depends(get_store_settings_repository),
    _admin: AuthenticatedUser = Depends(require_any_role(Role.ADMIN)),
) -> StoreSettingsSchema:
    try:
        settings = await UpdateStoreSettings(repository).execute(
            default_low_stock_threshold=get_low_stock_threshold_env_default(),
            cnpj=body.cnpj,
            store_name=body.store_name,
            contact_email=body.contact_email,
            contact_phone=body.contact_phone,
            store_address=body.store_address,
            low_stock_threshold=body.low_stock_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_schema(settings)
