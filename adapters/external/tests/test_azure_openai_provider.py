"""Testes "sandbox" do adapter real do Azure OpenAI — sem nenhuma
credencial nem chamada de rede de verdade. `respx` intercepta as chamadas
HTTP que o SDK da OpenAI (usado por baixo do langchain-openai) faz via
`httpx`, então exercitamos o código de produção de verdade (parsing de
request/response, propagação de erro) sem depender do serviço estar no ar.

Isto fecha o gap descrito na avaliação de estratégia de testes: até aqui só
`dev_llm_provider.py` (o fake de desenvolvimento) tinha teste — o adapter
real nunca tinha rodado nem uma vez, nem contra uma API simulada."""
from __future__ import annotations

import json

import httpx
import openai
import pytest
import respx

from adapters_external.ai.azure_openai_provider import AzureOpenAILLMProvider
from core_ai_assistant.domain import ChatMessage, Role

FAKE_ENDPOINT = "https://fake-resource.openai.azure.com"


@pytest.fixture
def provider() -> AzureOpenAILLMProvider:
    return AzureOpenAILLMProvider(
        endpoint=FAKE_ENDPOINT,
        api_key="fake-key-nao-e-credencial-real",
        chat_deployment="fake-chat-deployment",
        embedding_deployment="fake-embedding-deployment",
    )


def _chat_completion_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": 0,
            "model": "fake-chat-deployment",
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
    async def test_retorna_o_texto_da_resposta(self, provider: AzureOpenAILLMProvider) -> None:
        route = respx.post(
            url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/chat/completions.*"
        ).mock(return_value=_chat_completion_response("Temos vestidos florais em estoque."))

        reply = await provider.complete(
            system_prompt="Você é a assistente da loja Nick.",
            messages=[ChatMessage(role=Role.USER, content="Tem vestido floral?")],
        )

        assert reply == "Temos vestidos florais em estoque."
        assert route.called

    @respx.mock
    async def test_monta_system_prompt_e_historico_na_ordem_certa(
        self, provider: AzureOpenAILLMProvider
    ) -> None:
        route = respx.post(
            url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/chat/completions.*"
        ).mock(return_value=_chat_completion_response("ok"))

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

    @respx.mock
    async def test_erro_de_autenticacao_da_api_propaga_como_excecao_especifica(
        self, provider: AzureOpenAILLMProvider
    ) -> None:
        # Não engole o erro nem devolve string vazia — quem chama a porta
        # (AskAssistant) precisa saber que a chamada falhou de verdade.
        respx.post(url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/chat/completions.*").mock(
            return_value=httpx.Response(
                401,
                json={
                    "error": {
                        "message": "Incorrect API key provided",
                        "type": "invalid_request_error",
                        "code": "invalid_api_key",
                    }
                },
            )
        )

        with pytest.raises(openai.AuthenticationError):
            await provider.complete(system_prompt="s", messages=[])

    @respx.mock
    async def test_erro_5xx_da_api_propaga_como_excecao(
        self, provider: AzureOpenAILLMProvider
    ) -> None:
        respx.post(url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/chat/completions.*").mock(
            return_value=httpx.Response(
                500, json={"error": {"message": "internal error", "type": "server_error"}}
            )
        )

        with pytest.raises(openai.APIStatusError):
            await provider.complete(system_prompt="s", messages=[])


class TestEmbed:
    @respx.mock
    async def test_retorna_o_vetor_da_resposta(self, provider: AzureOpenAILLMProvider) -> None:
        respx.post(url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/embeddings.*").mock(
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

    @respx.mock
    async def test_nao_faz_chamada_de_rede_escondida_pro_tiktoken(
        self, provider: AzureOpenAILLMProvider
    ) -> None:
        # Regressão: sem check_embedding_ctx_length=False no adapter, esta
        # chamada faria uma requisição de verdade (fora do respx, via
        # `requests`/urllib3, não `httpx`) pro blob storage público da
        # Microsoft pra baixar o encoding do tiktoken — falha numa rede com
        # egress restrito. Aqui só a rota de embeddings está mockada; se o
        # adapter tentasse tiktoken, este teste falharia por tentar rede de
        # verdade (bloqueada neste ambiente) em vez de usar o mock abaixo.
        respx.post(url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/embeddings.*").mock(
            return_value=httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [{"object": "embedding", "index": 0, "embedding": [0.5]}],
                    "model": "fake-embedding-deployment",
                    "usage": {"prompt_tokens": 1, "total_tokens": 1},
                },
            )
        )

        vector = await provider.embed("x" * 5000)  # texto "grande" de propósito

        assert vector == [0.5]

    @respx.mock
    async def test_erro_da_api_propaga_como_excecao(
        self, provider: AzureOpenAILLMProvider
    ) -> None:
        respx.post(url__regex=rf"{FAKE_ENDPOINT}/openai/deployments/.*/embeddings.*").mock(
            return_value=httpx.Response(
                429, json={"error": {"message": "rate limited", "type": "rate_limit_error"}}
            )
        )

        with pytest.raises(openai.RateLimitError):
            await provider.embed("qualquer coisa")
