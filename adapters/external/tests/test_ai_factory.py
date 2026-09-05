from __future__ import annotations

import pytest

from adapters_external.ai.dev_llm_provider import DevLLMProvider
from adapters_external.ai.factory import get_llm_provider


def test_default_provider_e_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert isinstance(get_llm_provider(), DevLLMProvider)


def test_provider_dev_explicito(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "dev")
    assert isinstance(get_llm_provider(), DevLLMProvider)


def test_provider_azure_openai_sem_credencial_levanta_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure-openai")
    for var in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    ):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(NotImplementedError):
        get_llm_provider()


def test_provider_desconhecido_levanta_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "chatgpt-da-casa")
    with pytest.raises(ValueError):
        get_llm_provider()
