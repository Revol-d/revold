"""Testes "sandbox" do adapter DeepSeek + Azure OpenAI (ADR-0026) — sem
nenhuma credencial nem chamada de rede de verdade. `respx` intercepta as
chamadas HTTP que o SDK da OpenAI (usado por baixo do langchain-openai) faz
via `httpx` — tanto para o DeepSeek (`complete`) quanto para a Azure OpenAI
(`embed`) — mesmo padrão de test_azure_openai_provider.py.

O `complete()` fala com o DeepSeek; o `embed()` continua na Azure OpenAI
(o DeepSeek não tem endpoint de embeddings compatível) — os dois são
exercitados aqui separadamente."""
from __future__ import annotations

import json

import httpx
import openai
import pytest
import respx

from adapters_external.ai.deepseek_llm_provider import DeepSeekLLMProvider
from core_ai_assistant.domain import ChatMessage, Role

FAKE_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
FAKE_AZURE_ENDPOINT = "https://fake-resource.openai.azure.com"


@pytest.fixture
def provider() -> DeepSeekLLMProvider:
    return DeepSeekLLMProvider(
        deepseek_api_key="fake-deepseek-key-nao-e-real",
        deepseek_model="fake-deepseek-model",
        deepseek_base_url=FAKE_DEEPSEEK_BASE_URL,
        azure_endpoint=FAKE_AZURE_ENDPOINT,
        azure_api_key="fake-azure-key-nao-e-real",
        azure_embedding_deployment="fake-embedding-deployment",
    )


def _chat_completion_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": 0,
            "model": "fake-deepseek-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        },
    )


class TestComplete:
    @respx.mock
    async def test_retorna_o_texto_da_resposta(self, provider: DeepSeekLLMProvider) -> None:
        route = respx.post(f"{FAKE_DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=_chat_completion_response("Temos vestidos florais em estoque.")
        )

        reply = await provider.complete(
            system_prompt="Você é a assistente da loja Nick.",
            messages=[ChatMessage(role=Role.USER, content="Tem vestido floral?")],
        )

        assert reply == "Temos vestidos florais em estoque."
        assert route.called

    @respx.mock
    async def test_monta_system_prompt_e_historico_na_ordem_certa(
        self, provider: DeepSeekLLMProvider
    ) -> None:
        route = respx.post(f"{FAKE_DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=_chat_completion_response("ok")
        )

        await provider.complete(
            system_prompt="Você é a assistente da loja Nick.",
            messages=[
                ChatMessage(role=Role.USER, content="Oi"),
                ChatMessage(role=Role.ASSISTANT, content="Olá! Como posso ajudar?"),
                ChatMessage(role=Role.USER, content="Tem vestido azul?"),
            ],
        )

        sent = route.calls.last.request
        payload = json.loads(sent.content)
        roles = [m["role"] for m in payload["messages"]]
        assert roles == ["system", "user", "assistant", "user"]
        assert payload["messages"][0]["content"] == "Você é a assistente da loja Nick."
        assert payload["messages"][-1]["content"] == "Tem vestido azul?"
        assert payload["model"] == "fake-deepseek-model"

    @respx.mock
    async def test_erro_de_autenticacao_da_api_propaga_como_excecao_especifica(
        self, provider: DeepSeekLLMProvider
    ) -> None:
        respx.post(f"{FAKE_DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {
                        "message": "Authentication Fails",
                        "type": "invalid_request_error",
                        "code": "invalid_api_key",
                    }
                },
            )
        )

        with pytest.raises(openai.AuthenticationError):
            await provider.complete(system_prompt="s", messages=[])

    @respx.mock
    async def test_erro_5xx_da_api_propaga_como_excecao(self, provider: DeepSeekLLMProvider) -> None:
        respx.post(f"{FAKE_DEEPSEEK_BASE_URL}/chat/completions").mock(
            return_value=httpx.Response(
                500, json={"error": {"message": "internal error", "type": "server_error"}}
            )
        )

        with pytest.raises(openai.APIStatusError):
            await provider.complete(system_prompt="s", messages=[])


class TestEmbed:
    @respx.mock
    async def test_embed_usa_a_azure_openai_nao_o_deepseek(
        self, provider: DeepSeekLLMProvider
    ) -> None:
        # O ponto central desta ADR: embed() nunca deve chamar o DeepSeek —
        # não mockar nenhuma rota do DeepSeek aqui, só a da Azure, confirma
        # isso (uma chamada acidental ao DeepSeek derrubaria o teste por
        # rota não mockada).
        route = respx.post(
            url__regex=rf"{FAKE_AZURE_ENDPOINT}/openai/deployments/.*/embeddings.*"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
                    "model": "fake-embedding-deployment",
                    "usage": {"prompt_tokens": 3, "total_tokens": 3},
                },
            )
        )

        vector = await provider.embed("vestido floral de verão")

        assert vector == [0.1, 0.2, 0.3]
        assert route.called

    @respx.mock
    async def test_erro_da_api_propaga_como_excecao(self, provider: DeepSeekLLMProvider) -> None:
        respx.post(url__regex=rf"{FAKE_AZURE_ENDPOINT}/openai/deployments/.*/embeddings.*").mock(
            return_value=httpx.Response(
                429, json={"error": {"message": "rate limited", "type": "rate_limit_error"}}
            )
        )

        with pytest.raises(openai.RateLimitError):
            await provider.embed("qualquer coisa")
