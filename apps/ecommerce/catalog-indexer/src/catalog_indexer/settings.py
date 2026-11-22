"""Configuração do catalog-indexer. É o ÚNICO módulo do app que lê configuração do ambiente.

Lê pelo `revold_platform.configuration` (um parser só), e na CHAMADA de cada função, nunca no
import. As libs e o produto recebem configuração por parâmetro.

Os nomes e o significado de cada variável estão no `.env.example`.
"""

from __future__ import annotations

from revold_ai_assistant.adapters.llm.factory import LLMSettings
from revold_platform.configuration import env_snapshot, env_str

# Só valem em desenvolvimento local, fora do Compose.
_DEV_DATABASE_URL = (
    "mssql+aioodbc://sa:revold_dev_only_1@localhost:1433/revold"
    "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
)
_DEV_REDIS_URL = "redis://localhost:6379/0"


def database_url() -> str:
    return env_str("DATABASE_URL", _DEV_DATABASE_URL) or _DEV_DATABASE_URL


def redis_url() -> str:
    """Broker do Celery."""
    return env_str("REDIS_URL", _DEV_REDIS_URL) or _DEV_REDIS_URL


def llm_settings() -> LLMSettings:
    return LLMSettings.from_mapping(env_snapshot())
