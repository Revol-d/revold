"""Configuração do event-worker. É o ÚNICO módulo do app que lê configuração do ambiente.

Lê pelo `revold_platform.configuration` (um parser só), e na CHAMADA de cada função, nunca no
import. As libs e o produto recebem configuração por parâmetro.

Os nomes e o significado de cada variável estão no `.env.example`.
"""

from __future__ import annotations

from revold_ai_assistant.adapters.llm.factory import LLMSettings
from revold_messaging.webhook_factory import DEFAULT_WEBHOOK_SENDER_PROVIDER
from revold_notification.adapters.factory import NotificationSettings
from revold_platform.configuration import env_list, env_snapshot, env_str

# Só valem em desenvolvimento local, fora do Compose.
_DEV_DATABASE_URL = "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
_DEV_REDIS_URL = "redis://localhost:6379/0"


def database_url() -> str:
    return env_str("DATABASE_URL", _DEV_DATABASE_URL) or _DEV_DATABASE_URL


def redis_url() -> str:
    """Broker do Celery (ADR-0013)."""
    return env_str("REDIS_URL", _DEV_REDIS_URL) or _DEV_REDIS_URL


def llm_settings() -> LLMSettings:
    return LLMSettings.from_mapping(env_snapshot())


def notification_settings() -> NotificationSettings:
    return NotificationSettings.from_mapping(env_snapshot())


def webhook_sender_provider() -> str:
    return (
        env_str("WEBHOOK_SENDER_PROVIDER", DEFAULT_WEBHOOK_SENDER_PROVIDER)
        or DEFAULT_WEBHOOK_SENDER_PROVIDER
    )


def webhook_urls() -> list[str]:
    """Destinos de webhook de parceiro (ADR-0016). Lista vazia: nenhum parceiro configurado."""
    return env_list("WEBHOOK_URLS")
