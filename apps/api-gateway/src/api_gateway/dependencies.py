"""Injeção de dependência do api-gateway.

O api-gateway é a única camada que conhece FastAPI + a implementação
concreta dos adapters. Os cores nunca são importados fora daqui a não ser
pelas suas portas e casos de uso.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from adapters_external.ai.factory import get_llm_provider as _get_llm_provider
from adapters_external.checkout.whatsapp_clicktochat import WhatsAppClickToChatCheckout
from adapters_external.identity.factory import get_identity_provider as _get_identity_provider
from adapters_external.notification.logging_channel import LoggingNotificationChannel
from adapters_persistence.ai_assistant.repository import PostgresProductIndexRepository
from adapters_persistence.cart.redis_repository import RedisCartRepository
from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from adapters_persistence.identity.redis_session_repository import RedisSessionRepository
from adapters_persistence.inventory.repository import PostgresInventoryRepository
from adapters_persistence.redis_client import make_redis_client
from core_ai_assistant.ports import LLMProvider, ProductIndex
from core_cart.ports import CartRepository
from core_catalog.ports import ProductRepository
from core_communication.ports import CheckoutHandoff
from core_identity.ports import IdentityProvider, SessionRepository
from core_inventory.ports import InventoryRepository
from core_notification.ports import NotificationChannel

_engine = make_engine()
_session_factory = make_session_factory(_engine)
_redis_client = make_redis_client()
_notification_channel = LoggingNotificationChannel()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session


async def get_product_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProductRepository:
    return PostgresProductRepository(session)


def get_redis_client() -> Redis:
    return _redis_client


async def get_cart_repository(
    redis: Redis = Depends(get_redis_client),
) -> CartRepository:
    return RedisCartRepository(redis)


async def get_inventory_repository(
    session: AsyncSession = Depends(get_db_session),
) -> InventoryRepository:
    return PostgresInventoryRepository(session)


async def get_session_repository(
    redis: Redis = Depends(get_redis_client),
) -> SessionRepository:
    return RedisSessionRepository(redis)


def get_identity_provider() -> IdentityProvider:
    # Seleciona dev/azure-ad/google via AUTH_PROVIDER (ver
    # adapters_external.identity.factory e ADR-0003).
    return _get_identity_provider()


def get_checkout_handoff() -> CheckoutHandoff:
    # Única implementação hoje é o clique-para-conversar do WhatsApp
    # (ADR-0005). Trocar para a WhatsApp Business API oficial, quando
    # existir, é só mudar o que esta função retorna.
    return WhatsAppClickToChatCheckout()


def get_notification_channel() -> NotificationChannel:
    # Stand-in que só loga/guarda em memória (ver
    # adapters_external.notification.logging_channel) — trocar por
    # WhatsApp Business API ou e-mail real é só mudar o que esta função
    # retorna; a porta NotificationChannel não muda.
    return _notification_channel


def get_low_stock_threshold() -> int:
    return int(os.environ.get("LOW_STOCK_THRESHOLD", "5"))


def get_llm_provider() -> LLMProvider:
    # Seleciona dev/azure-openai via LLM_PROVIDER (ver
    # adapters_external.ai.factory e ADR-0011).
    return _get_llm_provider()


async def get_product_index(
    session: AsyncSession = Depends(get_db_session),
) -> ProductIndex:
    return PostgresProductIndexRepository(session)
