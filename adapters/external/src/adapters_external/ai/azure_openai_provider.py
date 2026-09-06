"""Implementação real (Azure OpenAI) da porta core_ai_assistant.ports.LLMProvider.

Testado via sandbox HTTP (respx, ver adapters/external/tests/
test_azure_openai_provider.py) — nunca contra a API de verdade, porque não
há credencial Azure OpenAI disponível no ambiente onde isto foi escrito (ver
ADR-0011 e a avaliação de planejamento, seção 3.3: toda integração externa
tem que ter porta + adapter sandbox testável, e o adapter real entra assim
que houver credencial, sem mudar quem chama a porta).
"""
from __future__ import annotations

from collections.abc import Sequence

from core_ai_assistant.domain import ChatMessage, Role


class AzureOpenAILLMProvider:
    """Implementa core_ai_assistant.ports.LLMProvider via langchain-openai."""

    provider_name = "azure-openai"

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        chat_deployment: str,
        embedding_deployment: str,
        api_version: str = "2024-08-01-preview",
    ) -> None:
        # Import adiado: só paga o custo de importar langchain-openai quando
        # este adapter é de fato selecionado (LLM_PROVIDER=azure-openai).
        from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
        from pydantic import SecretStr

        secret_api_key = SecretStr(api_key)
        self._chat = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=secret_api_key,
            azure_deployment=chat_deployment,
            api_version=api_version,
        )
        self._embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=endpoint,
            api_key=secret_api_key,
            azure_deployment=embedding_deployment,
            api_version=api_version,
            # Sem isto, langchain-openai baixa o arquivo de encoding do
            # tiktoken de um blob storage público da Microsoft na primeira
            # chamada (rede real, fora do controle do adapter) só pra
            # contar/cortar tokens localmente antes de mandar pra API. Numa
            # rede com egress restrito (como o Terraform deste projeto se
            # propõe a controlar) isso pode falhar silenciosamente na
            # primeira chamada em produção. Descrição de produto é curta o
            # bastante pra não precisar de corte local — deixa a Azure
            # rejeitar com 400 no caso raro de passar do limite, em vez de
            # depender dessa chamada de rede escondida.
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
