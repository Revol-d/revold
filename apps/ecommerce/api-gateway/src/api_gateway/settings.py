"""Configuração do api-gateway. É o ÚNICO módulo do app que lê configuração do ambiente.

Lê pelo `revold_platform.configuration` (um parser só), e na CHAMADA de cada função, nunca no
import. As libs e o produto recebem configuração por parâmetro: os grupos de cada provedor
(`LLMSettings`, `MediaStorageSettings`, `PaymentSettings`) são montados aqui e entregues prontos
às factories dos domínios.

Os nomes e o significado de cada variável estão no `.env.example`.
"""

from __future__ import annotations

from pathlib import Path

from revold_ai_assistant.adapters.llm.factory import LLMSettings
from revold_catalog.adapters.media.factory import MediaStorageSettings
from revold_identity.adapters.providers.factory import DEFAULT_AUTH_PROVIDER
from revold_payments.adapters.gateways.factory import PaymentSettings
from revold_platform.configuration import env_int, env_snapshot, env_str

# Só valem em desenvolvimento local, fora do Compose. Em qualquer outro ambiente a variável
# correspondente é obrigatória e vem do `.env`, do Compose ou do Key Vault.
_DEV_DATABASE_URL = "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
_DEV_AZURE_SQL_DATABASE_URL = (
    "mssql+aioodbc://sa:revold_dev_only_1@localhost:1433/revold"
    "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
)
_DEV_REDIS_URL = "redis://localhost:6379/0"

_DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def persistence_provider() -> str:
    """`postgres` (padrão) ou `azure-sql` -- ver o plano de migração Postgres -> Azure SQL
    (docs internos). Troca em andamento fase a fase; o default só muda num PR dedicado,
    depois de todos os domínios migrados e validados."""
    return env_str("PERSISTENCE_PROVIDER", _DEFAULT_PERSISTENCE_PROVIDER) or _DEFAULT_PERSISTENCE_PROVIDER


def database_url() -> str:
    if persistence_provider() == "azure-sql":
        return env_str("DATABASE_URL", _DEV_AZURE_SQL_DATABASE_URL) or _DEV_AZURE_SQL_DATABASE_URL
    return env_str("DATABASE_URL", _DEV_DATABASE_URL) or _DEV_DATABASE_URL


def redis_url() -> str:
    return env_str("REDIS_URL", _DEV_REDIS_URL) or _DEV_REDIS_URL


def event_publisher() -> str:
    """`celery` publica no broker; qualquer outro valor (ou ausente) usa o publisher em memória."""
    return env_str("EVENT_PUBLISHER", "memory") or "memory"


def auth_provider() -> str:
    return env_str("AUTH_PROVIDER", DEFAULT_AUTH_PROVIDER) or DEFAULT_AUTH_PROVIDER


def checkout_whatsapp_number() -> str:
    """Número que recebe o checkout por clique-para-conversar (ADR-0005). Vazio: não configurado."""
    return env_str("NICK_WHATSAPP_NUMBER", "") or ""


def llm_settings() -> LLMSettings:
    return LLMSettings.from_mapping(env_snapshot())


def media_storage_settings() -> MediaStorageSettings:
    return MediaStorageSettings.from_mapping(env_snapshot())


def media_local_dir() -> Path:
    """Pasta que o app serve em `/media` (os arquivos do adapter local de mídia, ADR-0015)."""
    return Path(media_storage_settings().local_dir)


def payment_settings() -> PaymentSettings:
    return PaymentSettings.from_mapping(env_snapshot())


def low_stock_threshold_default() -> int:
    """Piso do limiar de estoque baixo enquanto a loja não salvou o dela (ADR-0019)."""
    return env_int("LOW_STOCK_THRESHOLD", 5)


def session_cookie_secure() -> bool:
    """Cookie de sessão com `Secure`. Só `false` (qualquer caixa) desliga; o padrão é ligado."""
    return (env_str("SESSION_COOKIE_SECURE", "true") or "true").lower() != "false"


def public_api_rate_limit() -> int:
    return env_int("PUBLIC_API_RATE_LIMIT", 60)


def public_api_rate_limit_window_seconds() -> int:
    return env_int("PUBLIC_API_RATE_LIMIT_WINDOW_SECONDS", 60)
