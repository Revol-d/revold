"""Os clientes do protocolo OpenAI em sandbox HTTP (respx): sem credencial nem rede de verdade."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from revold_openai.chat import AzureOpenAIChat, OpenAICompatibleChat
from revold_openai.embeddings import AzureOpenAIEmbeddings
from revold_openai.messages import ChatTurn

_AZURE = "https://fake-resource.openai.azure.com"
_COMPATIBLE = "https://api.compatible.example"
_FAKE_KEY = "fake-key-nao-e-credencial-real"
_CONVERSATION = [
    ChatTurn(role="user", content="Oi"),
    ChatTurn(role="assistant", content="Olá!"),
    ChatTurn(role="user", content="Tem vestido azul?"),
]


def _chat_completion_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": 0,
            "model": "fake",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        },
    )


@respx.mock
async def test_azure_chat_sends_system_prompt_and_turns_in_order() -> None:
    route = respx.post(
        url__regex=rf"{_AZURE}/openai/deployments/fake-chat/chat/completions.*"
    ).mock(return_value=_chat_completion_response("Temos, sim."))
    chat = AzureOpenAIChat(endpoint=_AZURE, api_key=_FAKE_KEY, deployment="fake-chat")

    reply = await chat.complete(system_prompt="Você é a assistente.", turns=_CONVERSATION)

    assert reply == "Temos, sim."
    payload = json.loads(route.calls.last.request.content)
    assert [m["role"] for m in payload["messages"]] == ["system", "user", "assistant", "user"]
    assert payload["messages"][0]["content"] == "Você é a assistente."


@respx.mock
async def test_compatible_chat_calls_the_base_url_with_the_model_as_a_parameter() -> None:
    route = respx.post(f"{_COMPATIBLE}/chat/completions").mock(
        return_value=_chat_completion_response("ok")
    )
    chat = OpenAICompatibleChat(base_url=_COMPATIBLE, api_key=_FAKE_KEY, model="fake-model")

    reply = await chat.complete(system_prompt="s", turns=_CONVERSATION[:1])

    assert reply == "ok"
    assert json.loads(route.calls.last.request.content)["model"] == "fake-model"


@respx.mock
async def test_azure_embeddings_return_the_vector() -> None:
    respx.post(url__regex=rf"{_AZURE}/openai/deployments/fake-embedding/embeddings.*").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": "list",
                "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
                "model": "fake-embedding",
                "usage": {"prompt_tokens": 3, "total_tokens": 3},
            },
        )
    )
    embeddings = AzureOpenAIEmbeddings(
        endpoint=_AZURE, api_key=_FAKE_KEY, deployment="fake-embedding"
    )

    assert await embeddings.embed("vestido floral") == [0.1, 0.2, 0.3]


def test_chat_turn_is_immutable() -> None:
    turn = ChatTurn(role="user", content="oi")

    with pytest.raises(AttributeError):
        turn.content = "outra coisa"  # type: ignore[misc]
