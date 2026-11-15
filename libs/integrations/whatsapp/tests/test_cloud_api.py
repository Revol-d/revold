"""O cliente da Cloud API em sandbox HTTP (respx): formato do request, sem credencial real."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from revold_whatsapp.cloud_api import WhatsAppCloudClient, template_payload, text_payload

_URL = "https://graph.facebook.com/v20.0/1234567890/messages"
_ACCEPTED = {"messages": [{"id": "wamid.fake"}]}


@pytest.fixture
def client() -> WhatsAppCloudClient:
    return WhatsAppCloudClient(
        access_token="fake-access-token-nao-e-real", phone_number_id="1234567890"
    )


def test_text_payload_shape() -> None:
    assert text_payload(to="5511999999999", body="oi") == {
        "messaging_product": "whatsapp",
        "to": "5511999999999",
        "type": "text",
        "text": {"body": "oi"},
    }


def test_template_payload_carries_the_text_as_the_body_parameter() -> None:
    payload = template_payload(to="5511999999999", template_name="aviso", body_text="oi")

    assert payload["type"] == "template"
    assert payload["template"]["name"] == "aviso"
    assert payload["template"]["language"] == {"code": "pt_BR"}
    assert payload["template"]["components"][0]["parameters"] == [{"type": "text", "text": "oi"}]


@respx.mock
async def test_send_text_posts_with_the_bearer_token(client: WhatsAppCloudClient) -> None:
    route = respx.post(_URL).mock(return_value=httpx.Response(200, json=_ACCEPTED))

    await client.send_text(to="5511999999999", body="oi")

    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer fake-access-token-nao-e-real"
    assert json.loads(request.content)["text"]["body"] == "oi"


@respx.mock
async def test_send_template_posts_a_template_message(client: WhatsAppCloudClient) -> None:
    route = respx.post(_URL).mock(return_value=httpx.Response(200, json=_ACCEPTED))

    await client.send_template(to="5511999999999", template_name="aviso", body_text="oi")

    assert json.loads(route.calls[0].request.content)["type"] == "template"


@respx.mock
async def test_api_error_is_raised_not_swallowed(client: WhatsAppCloudClient) -> None:
    respx.post(_URL).mock(
        return_value=httpx.Response(400, json={"error": {"message": "fora da janela"}})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.send_text(to="5511999999999", body="oi")
