"""Geração de resposta por um modelo de chat no protocolo OpenAI (via langchain-openai).

Dois clientes, a mesma chamada `complete`:

- `AzureOpenAIChat`: um deployment pré-provisionado na Azure OpenAI;
- `OpenAICompatibleChat`: qualquer endpoint compatível com o formato OpenAI em que o modelo é só
  um parâmetro da chamada (DeepSeek, ADR-0026).

O import do `langchain-openai` é adiado para o construtor: só paga o custo quem de fato
seleciona um destes clientes.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from revold_openai.messages import ChatTurn

DEFAULT_AZURE_API_VERSION = "2024-08-01-preview"


async def _complete(chat_model: Any, *, system_prompt: str, turns: Sequence[ChatTurn]) -> str:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    lc_messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=system_prompt)
    ]
    for turn in turns:
        if turn.role == "user":
            lc_messages.append(HumanMessage(content=turn.content))
        else:
            lc_messages.append(AIMessage(content=turn.content))

    response = await chat_model.ainvoke(lc_messages)
    content = response.content
    return content if isinstance(content, str) else str(content)


class AzureOpenAIChat:
    """Chat de um deployment da Azure OpenAI."""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = DEFAULT_AZURE_API_VERSION,
    ) -> None:
        from langchain_openai import AzureChatOpenAI
        from pydantic import SecretStr

        self._chat = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=SecretStr(api_key),
            azure_deployment=deployment,
            api_version=api_version,
        )

    async def complete(self, *, system_prompt: str, turns: Sequence[ChatTurn]) -> str:
        return await _complete(self._chat, system_prompt=system_prompt, turns=turns)


class OpenAICompatibleChat:
    """Chat de um endpoint compatível com o formato OpenAI (o modelo é parâmetro da chamada)."""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        self._chat = ChatOpenAI(base_url=base_url, api_key=SecretStr(api_key), model=model)

    async def complete(self, *, system_prompt: str, turns: Sequence[ChatTurn]) -> str:
        return await _complete(self._chat, system_prompt=system_prompt, turns=turns)
