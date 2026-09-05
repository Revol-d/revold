"""Seleciona a implementação de LLMProvider a partir de LLM_PROVIDER.

Este é o único lugar que decide qual adapter usar — trocar de provedor em
produção é mudar a variável de ambiente, nunca importar um adapter
diferente manualmente em outro módulo (ver ADR-0011).
"""
from __future__ import annotations

import os

from core_ai_assistant.ports import LLMProvider

from adapters_external.ai.dev_llm_provider import DevLLMProvider


def get_llm_provider() -> LLMProvider:
    provider = os.environ.get("LLM_PROVIDER", "dev")
    if provider == "dev":
        return DevLLMProvider()
    if provider == "azure-openai":
        from adapters_external.ai.azure_openai_provider import AzureOpenAILLMProvider

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        chat_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        if not (endpoint and api_key and chat_deployment and embedding_deployment):
            raise NotImplementedError(
                "LLM_PROVIDER=azure-openai requer AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT e "
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT configurados (ver .env.example e ADR-0011)."
            )
        return AzureOpenAILLMProvider(
            endpoint=endpoint,
            api_key=api_key,
            chat_deployment=chat_deployment,
            embedding_deployment=embedding_deployment,
        )
    raise ValueError(f"LLM_PROVIDER desconhecido: {provider!r}")
