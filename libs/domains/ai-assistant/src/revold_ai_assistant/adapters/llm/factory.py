"""Seleciona a implementação de LLMProvider a partir de `LLMSettings`.

Este é o único lugar que decide qual adapter usar — trocar de provedor em
produção é mudar a configuração, nunca importar um adapter diferente
manualmente em outro módulo (ver ADR-0011).

Este módulo não lê o ambiente. O `settings.py` do app lê e entrega um
`LLMSettings` pronto (em geral via `LLMSettings.from_mapping(env_snapshot())`).
Os nomes das chaves são os do `.env.example`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from revold_ai_assistant.adapters.llm.dev_llm_provider import DevLLMProvider
from revold_ai_assistant.ports import LLMProvider

_DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@dataclass(frozen=True)
class LLMSettings:
    """Configuração do provedor de LLM. Segredo fica fora do `repr`."""

    provider: str = "dev"
    azure_endpoint: str | None = None
    azure_api_key: str | None = field(default=None, repr=False)
    azure_chat_deployment: str | None = None
    azure_embedding_deployment: str | None = None
    deepseek_api_key: str | None = field(default=None, repr=False)
    deepseek_model: str | None = None
    deepseek_base_url: str = _DEFAULT_DEEPSEEK_BASE_URL

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> LLMSettings:
        """Monta a configuração a partir de um mapeamento com as chaves do `.env.example`."""
        return cls(
            provider=values.get("LLM_PROVIDER", "dev"),
            azure_endpoint=values.get("AZURE_OPENAI_ENDPOINT"),
            azure_api_key=values.get("AZURE_OPENAI_API_KEY"),
            azure_chat_deployment=values.get("AZURE_OPENAI_DEPLOYMENT"),
            azure_embedding_deployment=values.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            deepseek_api_key=values.get("DEEPSEEK_API_KEY"),
            deepseek_model=values.get("DEEPSEEK_MODEL"),
            deepseek_base_url=values.get("DEEPSEEK_BASE_URL", _DEFAULT_DEEPSEEK_BASE_URL),
        )


def build_llm_provider(settings: LLMSettings | None = None) -> LLMProvider:
    settings = settings or LLMSettings()
    provider = settings.provider
    if provider == "dev":
        return DevLLMProvider()
    if provider == "azure-openai":
        from revold_ai_assistant.adapters.llm.azure_openai_provider import AzureOpenAILLMProvider

        if not (
            settings.azure_endpoint
            and settings.azure_api_key
            and settings.azure_chat_deployment
            and settings.azure_embedding_deployment
        ):
            raise NotImplementedError(
                "LLM_PROVIDER=azure-openai requer AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT e "
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT configurados (ver .env.example e ADR-0011)."
            )
        return AzureOpenAILLMProvider(
            endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            chat_deployment=settings.azure_chat_deployment,
            embedding_deployment=settings.azure_embedding_deployment,
        )
    if provider == "deepseek":
        from revold_ai_assistant.adapters.llm.deepseek_llm_provider import DeepSeekLLMProvider

        # Chat vai pro DeepSeek; embeddings continuam na Azure OpenAI (o
        # DeepSeek não tem endpoint compatível) — ver ADR-0026.
        if not (settings.deepseek_api_key and settings.deepseek_model):
            raise NotImplementedError(
                "LLM_PROVIDER=deepseek requer DEEPSEEK_API_KEY e DEEPSEEK_MODEL "
                "configurados (sem default de propósito — confira o nome do modelo "
                "atual em https://api-docs.deepseek.com/ antes de configurar; ver "
                ".env.example e ADR-0026)."
            )
        if not (
            settings.azure_endpoint
            and settings.azure_api_key
            and settings.azure_embedding_deployment
        ):
            raise NotImplementedError(
                "LLM_PROVIDER=deepseek usa a Azure OpenAI só para embeddings (o "
                "DeepSeek não tem endpoint compatível) — requer também "
                "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY e "
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT configurados (ver ADR-0026)."
            )
        return DeepSeekLLMProvider(
            deepseek_api_key=settings.deepseek_api_key,
            deepseek_model=settings.deepseek_model,
            deepseek_base_url=settings.deepseek_base_url,
            azure_endpoint=settings.azure_endpoint,
            azure_api_key=settings.azure_api_key,
            azure_embedding_deployment=settings.azure_embedding_deployment,
        )
    raise ValueError(f"LLM_PROVIDER desconhecido: {provider!r}")
