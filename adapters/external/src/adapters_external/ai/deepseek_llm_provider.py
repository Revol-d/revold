"""Implementação real (DeepSeek + Azure OpenAI) da porta
core_ai_assistant.ports.LLMProvider (ADR-0026).

Decisão do Samuel: o chat (`complete`) vai para o DeepSeek — API compatível
com o formato OpenAI, sem "deployment" pré-provisionado como na Azure; o
nome do modelo é só um parâmetro de cada chamada (`DEEPSEEK_MODEL`), não um
recurso configurado antes (diferente de `AzureOpenAILLMProvider`,
`AZURE_OPENAI_DEPLOYMENT`). O DeepSeek não tem endpoint de embeddings
compatível com o formato OpenAI, então `embed()` continua na Azure OpenAI —
mesmas credenciais/deployment que `AzureOpenAILLMProvider` já usa
(`AZURE_OPENAI_ENDPOINT`/`AZURE_OPENAI_API_KEY`/
`AZURE_OPENAI_EMBEDDING_DEPLOYMENT`).

Testado via sandbox HTTP (respx, ver adapters/external/tests/
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

from core_ai_assistant.domain import ChatMessage, Role


class DeepSeekLLMProvider:
    """Implementa core_ai_assistant.ports.LLMProvider via langchain-openai:
    `complete()` fala com o DeepSeek (API OpenAI-compatible), `embed()` fala
    com a Azure OpenAI."""

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
        azure_api_version: str = "2024-08-01-preview",
    ) -> None:
        # Import adiado: só paga o custo de importar langchain-openai quando
        # este adapter é de fato selecionado (LLM_PROVIDER=deepseek).
        from langchain_openai import AzureOpenAIEmbeddings, ChatOpenAI
        from pydantic import SecretStr

        self._chat = ChatOpenAI(
            base_url=deepseek_base_url,
            api_key=SecretStr(deepseek_api_key),
            model=deepseek_model,
        )
        self._embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=azure_endpoint,
            api_key=SecretStr(azure_api_key),
            azure_deployment=azure_embedding_deployment,
            api_version=azure_api_version,
            # Mesmo raciocínio de AzureOpenAILLMProvider — evita a chamada de
            # rede escondida do tiktoken pro blob storage público da
            # Microsoft (ver docstring daquele adapter).
            check_embedding_ctx_length=False,
        )

    async def embed(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=system_prompt)
        ]
        for message in messages:
            if message.role == Role.USER:
                lc_messages.append(HumanMessage(content=message.content))
            else:
                lc_messages.append(AIMessage(content=message.content))

        response = await self._chat.ainvoke(lc_messages)
        content = response.content
        return content if isinstance(content, str) else str(content)
