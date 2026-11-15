"""Portas (interfaces) que `ai-assistant` espera que a infraestrutura implemente.

Qualquer adapter (Azure OpenAI, um dev stand-in, um fake em memória para
teste etc.) implementa estes Protocols. `ai-assistant` nunca importa
langchain-openai nem SQLAlchemy/driver de banco diretamente fora de si
mesmo — só através destas portas.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from revold_ai_assistant.domain import ChatMessage, RetrievedProduct


class LLMProvider(Protocol):
    provider_name: str

    async def embed(self, text: str) -> list[float]:
        """Vetor de embedding do texto, usado tanto para indexar produtos
        quanto para buscar por similaridade (RAG)."""
        ...

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        """Gera a próxima resposta do assistente dado o prompt de sistema
        (contexto de produtos recuperados) e o histórico da conversa."""
        ...


class ProductIndex(Protocol):
    """Índice vetorial do catálogo (RAG). Vive em `ai-assistant`, não em
    `catalog` — os dois cores nunca se importam (ADR-0002); popular este
    índice a partir do catálogo é orquestração cross-core (ver
    apps/ecommerce/catalog-indexer)."""

    async def upsert(self, *, sku: str, name: str, description: str, embedding: list[float]) -> None:
        ...

    async def search(self, *, embedding: list[float], limit: int) -> list[RetrievedProduct]:
        ...
