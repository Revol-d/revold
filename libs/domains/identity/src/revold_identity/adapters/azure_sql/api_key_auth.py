"""Implementação Azure SQL da porta revold_identity.ports.ApiKeyAuth (ADR-0016)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revold_identity.adapters.azure_sql.api_key_models import ApiKeyModel
from revold_identity.domain import ApiKeyNotFound, ApiKeyPrincipal

_KEY_PREFIX = "rvld"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class AzureSqlApiKeyAuth:
    """Implementa revold_identity.ports.ApiKeyAuth via SQLAlchemy async contra o
    Azure SQL Database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, *, name: str) -> tuple[ApiKeyPrincipal, str]:
        raw_key = f"{_KEY_PREFIX}_{secrets.token_urlsafe(32)}"
        model = ApiKeyModel(
            key_id=str(uuid.uuid4()),
            name=name,
            key_hash=_hash_key(raw_key),
            created_at=datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.commit()
        return ApiKeyPrincipal(key_id=model.key_id, name=model.name), raw_key

    async def resolve(self, raw_key: str) -> ApiKeyPrincipal | None:
        stmt = select(ApiKeyModel).where(
            ApiKeyModel.key_hash == _hash_key(raw_key), ApiKeyModel.revoked_at.is_(None)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ApiKeyPrincipal(key_id=model.key_id, name=model.name)

    async def revoke(self, key_id: str) -> None:
        model = await self._session.get(ApiKeyModel, key_id)
        if model is None:
            raise ApiKeyNotFound(key_id)
        model.revoked_at = datetime.now(UTC)
        await self._session.commit()
