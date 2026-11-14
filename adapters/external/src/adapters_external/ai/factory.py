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
    if provider == "deepseek":
        from adapters_external.ai.deepseek_llm_provider import DeepSeekLLMProvider

        # Chat vai pro DeepSeek; embeddings continuam na Azure OpenAI (o
        # DeepSeek não tem endpoint compatível) — ver ADR-0026.
        deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        deepseek_model = os.environ.get("DEEPSEEK_MODEL")
        deepseek_base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        azure_embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        if not (deepseek_api_key and deepseek_model):
            raise NotImplementedError(
                "LLM_PROVIDER=deepseek requer DEEPSEEK_API_KEY e DEEPSEEK_MODEL "
                "configurados (sem default de propósito — confira o nome do modelo "
                "atual em https://api-docs.deepseek.com/ antes de configurar; ver "
                ".env.example e ADR-0026)."
            )
        if not (azure_endpoint and azure_api_key and azure_embedding_deployment):
            raise NotImplementedError(
                "LLM_PROVIDER=deepseek usa a Azure OpenAI só para embeddings (o "
                "DeepSeek não tem endpoint compatível) — requer também "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY e "
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT configurados (ver ADR-0026)."
            )
        return DeepSeekLLMProvider(
            deepseek_api_key=deepseek_api_key,
            deepseek_model=deepseek_model,
            deepseek_base_url=deepseek_base_url,
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_api_key,
            azure_embedding_deployment=azure_embedding_deployment,
        )
    raise ValueError(f"LLM_PROVIDER desconhecido: {provider!r}")
