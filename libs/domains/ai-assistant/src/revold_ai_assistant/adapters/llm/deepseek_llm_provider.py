"""Implementação real (DeepSeek + Azure OpenAI) da porta
revold_ai_assistant.ports.LLMProvider (ADR-0026).

Decisão do Samuel: o chat (`complete`) vai para o DeepSeek — API compatível
com o formato OpenAI, sem "deployment" pré-provisionado como na Azure; o
nome do modelo é só um parâmetro de cada chamada (`DEEPSEEK_MODEL`), não um
recurso configurado antes (diferente de `AzureOpenAILLMProvider`,
`AZURE_OPENAI_DEPLOYMENT`). O DeepSeek não tem endpoint de embeddings
compatível com o formato OpenAI, então `embed()` continua na Azure OpenAI —
mesmas credenciais/deployment que `AzureOpenAILLMProvider` já usa
(`AZURE_OPENAI_ENDPOINT`/`AZURE_OPENAI_API_KEY`/
`AZURE_OPENAI_EMBEDDING_DEPLOYMENT`).

Este adapter traduz a conversa do domínio para o formato do cliente. Quem
fala com o DeepSeek e com a Azure são os clientes de `revold_openai`
(libs/integrations/openai).

Testado via sandbox HTTP (respx, ver libs/domains/ai-assistant/tests/
test_deepseek_llm_provider.py) — nunca contra a API de verdade, porque não
há credencial real disponível no ambiente onde isto foi escrito (mesma
ressalva de ADR-0011/ADR-0024/ADR-0025: sandbox valida o formato
documentado, não o comportamento real do serviço).

**Nomes de modelo do DeepSeek mudam com o tempo** (achado ao pesquisar para
escrever este adapter: `deepseek-chat`/`deepseek-reasoner`, os nomes mais
conhecidos, estavam sendo depreciados a favor de nomes novos na época desta
sessão) — por isso `DEEPSEEK_MODEL` não tem valor default aqui, igual
`AZURE_OPENAI_DEPLOYMENT` não tem: confira o nome atual em
https://api-docs.deepseek.com/ antes de configurar."""
from __future__ import annotations

from collections.abc import Sequence

from revold_ai_assistant.adapters.llm.turns import to_chat_turns
from revold_ai_assistant.domain import ChatMessage
from revold_openai.chat import DEFAULT_AZURE_API_VERSION, OpenAICompatibleChat
from revold_openai.embeddings import AzureOpenAIEmbeddings


class DeepSeekLLMProvider:
    """Implementa revold_ai_assistant.ports.LLMProvider: `complete()` fala com
    o DeepSeek (API OpenAI-compatible), `embed()` fala com a Azure OpenAI."""

    provider_name = "deepseek"

    def __init__(
        self,
        *,
        deepseek_api_key: str,
        deepseek_model: str,
        deepseek_base_url: str,
        azure_endpoint: str,
        azure_api_key: str,
        azure_embedding_deployment: str,
        azure_api_version: str = DEFAULT_AZURE_API_VERSION,
    ) -> None:
        self._chat = OpenAICompatibleChat(
            base_url=deepseek_base_url,
            api_key=deepseek_api_key,
            model=deepseek_model,
        )
        self._embeddings = AzureOpenAIEmbeddings(
            endpoint=azure_endpoint,
            api_key=azure_api_key,
            deployment=azure_embedding_deployment,
            api_version=azure_api_version,
        )

    async def embed(self, text: str) -> list[float]:
        return await self._embeddings.embed(text)

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        return await self._chat.complete(system_prompt=system_prompt, turns=to_chat_turns(messages))
