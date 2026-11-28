"""Injeção de dependência do api-gateway.

O api-gateway é a única camada que conhece FastAPI + a implementação
concreta dos adapters. Os domínios nunca são importados fora daqui a não ser
pelas suas portas e casos de uso. A configuração vem de `api_gateway.settings`,
o único módulo do app que lê o ambiente.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api_gateway import settings
from revold_ai_assistant.adapters.llm.factory import build_llm_provider
from revold_ai_assistant.adapters.postgres.repository import PostgresProductIndexRepository
from revold_ai_assistant.ports import LLMProvider, ProductIndex
from revold_cart.adapters.redis.repository import RedisCartRepository
from revold_cart.ports import CartRepository
from revold_catalog.adapters.media.factory import build_media_storage
from revold_catalog.adapters.postgres.repository import PostgresProductRepository
from revold_catalog.ports import MediaStorage, ProductRepository
from revold_communication.adapters.whatsapp_clicktochat import WhatsAppClickToChatCheckout
from revold_communication.ports import CheckoutHandoff
from revold_identity.adapters.postgres.api_key_auth import PostgresApiKeyAuth
from revold_identity.adapters.providers.factory import build_identity_provider
from revold_identity.adapters.redis.rate_limiter import RedisRateLimiter
from revold_identity.adapters.redis.session_repository import RedisSessionRepository
from revold_identity.ports import ApiKeyAuth, IdentityProvider, RateLimiter, SessionRepository
from revold_inventory.adapters.factory import build_inventory_repository
from revold_inventory.ports import InventoryRepository
from revold_notification.adapters.logging_channel import LoggingNotificationChannel
from revold_notification.ports import NotificationChannel
from revold_orders.adapters.factory import build_order_repository
from revold_orders.ports import OrderRepository
from revold_payments.adapters.factory import build_charge_repository
from revold_payments.adapters.gateways.factory import build_payment_gateway
from revold_payments.ports import ChargeRepository, PaymentGateway
from revold_platform.events.in_memory_publisher import InMemoryEventPublisher
from revold_platform.events.ports import EventPublisher
from revold_platform.observability.ports import MetricsPublisher
from revold_prometheus.metrics_publisher import PrometheusMetricsPublisher
from revold_redis.client import make_redis_client
from revold_store_settings.adapters.factory import build_store_settings_repository
from revold_store_settings.ports import StoreSettingsRepository

if settings.persistence_provider() == "azure-sql":
    # Seleciona o engine/sessão do dialeto certo via PERSISTENCE_PROVIDER (ver o plano de
    # migração Postgres -> Azure SQL, docs internos). Só a construção do engine mora aqui;
    # qual classe de repositório embrulha a sessão é decidido em cada
    # `adapters/factory.py` de domínio (ver get_store_settings_repository abaixo).
    from revold_azure_sql.db import make_engine, make_session_factory
else:
    from revold_postgres.db import make_engine, make_session_factory

_engine = make_engine(settings.database_url())
_session_factory = make_session_factory(_engine)
_redis_client = make_redis_client(settings.redis_url())
_notification_channel = LoggingNotificationChannel()
_metrics_publisher = PrometheusMetricsPublisher()
_event_publisher: EventPublisher = InMemoryEventPublisher()
if settings.event_publisher() == "celery":
    # Import adiado: só puxa o cliente Celery quando de fato configurado
    # para usá-lo (ver ADR-0013) — mantém o api-gateway funcionando sem
    # Redis/worker em dev, com EVENT_PUBLISHER não setado (default:
    # InMemoryEventPublisher, que só loga e não tem consumidor real).
    from revold_messaging.celery_publisher import CeleryEventPublisher

    _event_publisher = CeleryEventPublisher(broker_url=settings.redis_url())


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
    # Seleciona postgres/azure-sql via PERSISTENCE_PROVIDER (ver
    # revold_inventory.adapters.factory e o plano de migração Postgres -> Azure SQL,
    # docs internos).
    return build_inventory_repository(session, settings.persistence_provider())


async def get_session_repository(
    redis: Redis = Depends(get_redis_client),
) -> SessionRepository:
    return RedisSessionRepository(redis)


def get_identity_provider() -> IdentityProvider:
    # Seleciona dev/azure-ad/google via AUTH_PROVIDER (ver
    # revold_identity.adapters.providers.factory e ADR-0003).
    return build_identity_provider(settings.auth_provider())


def get_checkout_handoff() -> CheckoutHandoff:
    # Única implementação hoje é o clique-para-conversar do WhatsApp
    # (ADR-0005). Trocar para a WhatsApp Business API oficial, quando
    # existir, é só mudar o que esta função retorna.
    return WhatsAppClickToChatCheckout(settings.checkout_whatsapp_number())


def get_notification_channel() -> NotificationChannel:
    # Stand-in que só loga/guarda em memória (ver
    # revold_notification.adapters.logging_channel) — trocar por
    # WhatsApp Business API ou e-mail real é só mudar o que esta função
    # retorna; a porta NotificationChannel não muda.
    return _notification_channel


async def get_order_repository(
    session: AsyncSession = Depends(get_db_session),
) -> OrderRepository:
    # Seleciona postgres/azure-sql via PERSISTENCE_PROVIDER (ver
    # revold_orders.adapters.factory e o plano de migração Postgres -> Azure SQL,
    # docs internos).
    return build_order_repository(session, settings.persistence_provider())


async def get_charge_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ChargeRepository:
    # Seleciona postgres/azure-sql via PERSISTENCE_PROVIDER (ver
    # revold_payments.adapters.factory e o plano de migração Postgres -> Azure SQL,
    # docs internos).
    return build_charge_repository(session, settings.persistence_provider())


def get_payment_gateway() -> PaymentGateway:
    # Seleciona fake/mercado_pago via PAYMENT_PROVIDER (ver
    # revold_payments.adapters.gateways.factory e ADR-0024).
    return build_payment_gateway(settings.payment_settings())


async def get_store_settings_repository(
    session: AsyncSession = Depends(get_db_session),
) -> StoreSettingsRepository:
    # Seleciona postgres/azure-sql via PERSISTENCE_PROVIDER (ver
    # revold_store_settings.adapters.factory e o plano de migração Postgres -> Azure SQL,
    # docs internos). O raciocínio "sempre Postgres" das ADR-0016/0019/0023/0024 vale até
    # essa migração terminar e uma ADR nova substituir essas quatro.
    return build_store_settings_repository(session, settings.persistence_provider())


def get_low_stock_threshold_env_default() -> int:
    """Valor de LOW_STOCK_THRESHOLD (env var) — usado como piso enquanto a
    Nick não salvou nenhuma configuração em /configuracoes (ADR-0019) e
    passado como `default_low_stock_threshold` para os casos de uso de
    revold_store_settings. Não é, sozinho, o limiar efetivo — ver
    `get_low_stock_threshold` abaixo."""
    return settings.low_stock_threshold_default()


async def get_low_stock_threshold(
    repository: StoreSettingsRepository = Depends(get_store_settings_repository),
) -> int:
    # Antes do ADR-0019, este valor só vinha de LOW_STOCK_THRESHOLD (env
    # var), fixo até o próximo deploy. Agora é lido da configuração da loja
    # (editável pela Nick em /configuracoes, sem precisar de deploy) — a
    # env var continua valendo como default até a Nick configurar algo pela
    # primeira vez (GetStoreSettings cai nela quando não há registro salvo),
    # então quem nunca abriu a tela de configurações não percebe mudança
    # nenhuma de comportamento.
    from revold_store_settings.application.use_cases import GetStoreSettings

    store_settings = await GetStoreSettings(repository).execute(
        default_low_stock_threshold=get_low_stock_threshold_env_default()
    )
    return store_settings.low_stock_threshold


def get_llm_provider() -> LLMProvider:
    # Seleciona dev/azure-openai/deepseek via LLM_PROVIDER (ver
    # revold_ai_assistant.adapters.llm.factory e ADR-0011).
    return build_llm_provider(settings.llm_settings())


async def get_product_index(
    session: AsyncSession = Depends(get_db_session),
) -> ProductIndex:
    return PostgresProductIndexRepository(session)


def get_media_storage() -> MediaStorage:
    # Seleciona local/azure-blob via MEDIA_STORAGE_PROVIDER (ver
    # revold_catalog.adapters.media.factory e ADR-0015).
    return build_media_storage(settings.media_storage_settings())


def get_event_publisher() -> EventPublisher:
    # Seleciona memory/celery via EVENT_PUBLISHER (ver
    # revold_messaging e ADR-0013). Default é o publisher em
    # memória — eventos são aceitos e logados, mas sem consumidor real até
    # EVENT_PUBLISHER=celery + um worker rodando (apps/ecommerce/event-worker).
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
