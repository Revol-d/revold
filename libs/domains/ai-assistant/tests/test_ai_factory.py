from __future__ import annotations

import pytest

from revold_ai_assistant.adapters.llm.dev_llm_provider import DevLLMProvider
from revold_ai_assistant.adapters.llm.factory import LLMSettings, build_llm_provider


def test_default_provider_e_dev() -> None:
    assert isinstance(build_llm_provider(), DevLLMProvider)


def test_mapeamento_vazio_cai_no_provider_dev() -> None:
    assert isinstance(build_llm_provider(LLMSettings.from_mapping({})), DevLLMProvider)


def test_provider_dev_explicito() -> None:
    settings = LLMSettings.from_mapping({"LLM_PROVIDER": "dev"})
    assert isinstance(build_llm_provider(settings), DevLLMProvider)


def test_provider_azure_openai_sem_credencial_levanta_not_implemented() -> None:
    settings = LLMSettings.from_mapping({"LLM_PROVIDER": "azure-openai"})
    with pytest.raises(NotImplementedError):
        build_llm_provider(settings)


def test_provider_deepseek_sem_credencial_levanta_not_implemented() -> None:
    settings = LLMSettings.from_mapping({"LLM_PROVIDER": "deepseek"})
    with pytest.raises(NotImplementedError):
        build_llm_provider(settings)


def test_provider_desconhecido_levanta_value_error() -> None:
    settings = LLMSettings.from_mapping({"LLM_PROVIDER": "chatgpt-da-casa"})
    with pytest.raises(ValueError):
        build_llm_provider(settings)


def test_from_mapping_le_as_chaves_do_env_example() -> None:
    settings = LLMSettings.from_mapping(
        {
            "LLM_PROVIDER": "azure-openai",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "chave-de-teste",
            "AZURE_OPENAI_DEPLOYMENT": "chat",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "embeddings",
        }
    )

    assert settings.provider == "azure-openai"
    assert settings.azure_endpoint == "https://example.openai.azure.com"
    assert settings.azure_chat_deployment == "chat"
    assert settings.azure_embedding_deployment == "embeddings"
    assert settings.deepseek_base_url == "https://api.deepseek.com"


def test_segredo_nao_aparece_no_repr() -> None:
    settings = LLMSettings(azure_api_key="chave-de-teste", deepseek_api_key="outra-chave")
    assert "chave-de-teste" not in repr(settings)
    assert "outra-chave" not in repr(settings)
