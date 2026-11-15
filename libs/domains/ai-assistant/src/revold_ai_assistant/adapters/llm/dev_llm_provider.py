"""Implementação dev da porta revold_ai_assistant.ports.LLMProvider (ADR-0011).

Não chama nenhum modelo de verdade — embed() é determinístico (mesmo texto
sempre gera o mesmo vetor, via seed de hash) e complete() é uma resposta
baseada em regra simples. Serve para exercitar toda a porta LLMProvider e o
fluxo do LangGraph (retrieve -> generate -> decide_escalation) em
desenvolvimento e teste, sem depender de credencial do Azure OpenAI — mesmo
espírito do DevIdentityProvider (`identity`) e do LoggingNotificationChannel
(`notification`).
"""
from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence

from revold_ai_assistant.domain import ChatMessage, Role

# Mesma dimensão do text-embedding-3-small (Azure OpenAI) — ver ADR-0011,
# para que trocar de provider não exija nova migração da coluna vector.
EMBEDDING_DIMENSIONS = 1536


class DevLLMProvider:
    """Implementa revold_ai_assistant.ports.LLMProvider."""

    provider_name = "dev"

    async def embed(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIMENSIONS)]

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        last_user = next(
            (message.content for message in reversed(messages) if message.role == Role.USER),
            "",
        )
        if "Produtos do catálogo" in system_prompt:
            return (
                f'[dev] Encontrei algumas opções relacionadas a "{last_user}". '
                "(uma resposta de verdade virá do Azure OpenAI quando configurado)"
            )
        return (
            f'[dev] Não encontrei produtos relacionados a "{last_user}". '
            "Fale com a Nick pelo WhatsApp para mais detalhes."
        )
