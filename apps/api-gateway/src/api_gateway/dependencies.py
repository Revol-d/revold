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
from adapters_external.media.factory import get_media_storage as _get_media_storage
from adapters_external.notification.logging_channel import LoggingNotificationChannel
from adapters_external.observability.prometheus_metrics_publisher import (
    PrometheusMetricsPublisher,
)
from adapters_messaging.events.in_memory_publisher import InMemoryEventPublisher
from adapters_persistence.ai_assistant.repository import PostgresProductIndexRepository
from adapters_persistence.cart.redis_repository import RedisCartRepository
from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from adapters_persistence.identity.postgres_api_key_auth import PostgresApiKeyAuth
from adapters_persistence.identity.redis_rate_limiter import RedisRateLimiter
from adapters_persistence.identity.redis_session_repository import RedisSessionRepository
from adapters_persistence.inventory.repository import PostgresInventoryRepository
from adapters_persistence.redis_client import make_redis_client
from core_ai_assistant.ports import LLMProvider, ProductIndex
from core_cart.ports import CartRepository
from core_catalog.ports import MediaStorage, ProductRepository
from core_communication.ports import CheckoutHandoff
from core_events.ports import EventPublisher
from core_identity.ports import ApiKeyAuth, IdentityProvider, RateLimiter, SessionRepository
from core_inventory.ports import InventoryRepository
from core_notification.ports import NotificationChannel
from core_observability.ports import MetricsPublisher

_engine = make_engine()
_session_factory = make_session_factory(_engine)
_redis_client = make_redis_client()
_notification_channel = LoggingNotificationChannel()
_metrics_publisher = PrometheusMetricsPublisher()
_event_publisher: EventPublisher = InMemoryEventPublisher()
if os.environ.get("EVENT_PUBLISHER") == "celery":
    # Import adiado: só puxa o cliente Celery quando de fato configurado
    # para usá-lo (ver ADR-0013) — mantém o api-gateway funcionando sem
    # Redis/worker em dev, com EVENT_PUBLISHER não setado (default:
    # InMemoryEventPublisher, que só loga e não tem consumidor real).
    from adapters_messaging.events.celery_publisher import CeleryEventPublisher

    _event_publisher = CeleryEventPublisher()


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


def get_media_storage() -> MediaStorage:
    # Seleciona local/azure-blob via MEDIA_STORAGE_PROVIDER (ver
    # adapters_external.media.factory e ADR-0015).
    return _get_media_storage()


def get_event_publisher() -> EventPublisher:
    # Seleciona memory/celery via EVENT_PUBLISHER (ver
    # adapters_messaging.events e ADR-0013). Default é o publisher em
    # memória — eventos são aceitos e logados, mas sem consumidor real até
    # EVENT_PUBLISHER=celery + um worker rodando (workers/event-worker).
    return _event_publisher


async def get_api_key_auth(
    session: AsyncSession = Depends(get_db_session),
) -> ApiKeyAuth:
    # Sempre Postgres (ADR-0016) — diferente de LLM_PROVIDER/AUTH_PROVIDER,
    # não há aqui um "provedor de nuvem" para trocar por env var: API key é
    # sempre um dado nosso, guardado no nosso banco.
    return PostgresApiKeyAuth(session)


def get_rate_limiter(redis: Redis = Depends(get_redis_client)) -> RateLimiter:
    # Sempre Redis (ADR-0016) — já é infraestrutura self-hosted do próprio
    # compose, sem credencial nenhuma envolvida.
    return RedisRateLimiter(redis)


def get_metrics_publisher() -> MetricsPublisher:
    # Singleton de processo (ADR-0017): um Counter/Histogram do
    # prometheus_client acumula estado entre chamadas — teria que ser um
    # só, não um novo por requisição, senão cada scrape veria os
    # contadores zerados.
    return _metrics_publisher


def get_metrics_registry():
    # Usado só por api_gateway.main no endpoint /metrics (não é uma
    # dependência de rota comum — o próprio scrape do Prometheus é quem
    # "chama" esse endpoint, sem passar por nenhum caso de uso).
    return _metrics_publisher.registry
