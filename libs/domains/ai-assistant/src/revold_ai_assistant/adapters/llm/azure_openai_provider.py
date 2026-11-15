"""Implementação real (Azure OpenAI) da porta revold_ai_assistant.ports.LLMProvider.

Este adapter traduz a conversa do domínio para o formato do cliente. Quem
fala com a Azure são os clientes de `revold_openai` (libs/integrations/openai).

Testado via sandbox HTTP (respx, ver libs/domains/ai-assistant/tests/
test_azure_openai_provider.py) — nunca contra a API de verdade, porque não
há credencial Azure OpenAI disponível no ambiente onde isto foi escrito (ver
ADR-0011 e a avaliação de planejamento, seção 3.3: toda integração externa
tem que ter porta + adapter sandbox testável, e o adapter real entra assim
que houver credencial, sem mudar quem chama a porta).
"""

from __future__ import annotations

from collections.abc import Sequence

from revold_ai_assistant.adapters.llm.turns import to_chat_turns
from revold_ai_assistant.domain import ChatMessage
from revold_openai.chat import DEFAULT_AZURE_API_VERSION, AzureOpenAIChat
from revold_openai.embeddings import AzureOpenAIEmbeddings


class AzureOpenAILLMProvider:
    """Implementa revold_ai_assistant.ports.LLMProvider com a Azure OpenAI."""

    provider_name = "azure-openai"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        chat_deployment: str,
        embedding_deployment: str,
        api_version: str = DEFAULT_AZURE_API_VERSION,
    ) -> None:
        self._chat = AzureOpenAIChat(
            endpoint=endpoint,
            api_key=api_key,
            deployment=chat_deployment,
            api_version=api_version,
        )
        self._embeddings = AzureOpenAIEmbeddings(
            endpoint=endpoint,
            api_key=api_key,
            deployment=embedding_deployment,
            api_version=api_version,
        )

    async def embed(self, text: str) -> list[float]:
        return await self._embeddings.embed(text)

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        return await self._chat.complete(system_prompt=system_prompt, turns=to_chat_turns(messages))
