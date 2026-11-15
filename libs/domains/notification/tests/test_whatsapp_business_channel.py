"""Testes "sandbox" do adapter real de WhatsApp Business Platform (Meta
Cloud API) — sem nenhuma credencial nem chamada de rede de verdade.
`respx` intercepta as chamadas HTTP que o adapter faz via `httpx`,
simulando os formatos de request/response documentados publicamente pela
Meta Cloud API.

Diferente de Azurite (test_azure_blob_storage.py) ou aiosmtpd
(test_smtp_channel.py), não existe um emulador oficial da Meta Cloud API
que fale o protocolo de verdade — então, diferente daqueles, isto não é
uma validação contra o protocolo real, só contra o formato documentado. A
próxima validação real só acontece com um número de teste + access token
da Meta, que só o Samuel pode gerar (ver docstring de
whatsapp_business_channel.py e ADR-0025)."""
from __future__ import annotations

import httpx
import pytest
import respx

from revold_notification.adapters.whatsapp_business_channel import (
    WhatsAppBusinessNotificationChannel,
)
from revold_notification.domain import Notification

_URL = "https://graph.facebook.com/v20.0/1234567890/messages"


@pytest.fixture
def channel() -> WhatsAppBusinessNotificationChannel:
    return WhatsAppBusinessNotificationChannel(
        access_token="fake-access-token-nao-e-real",
        phone_number_id="1234567890",
        recipient_number="5511999999999",
    )


@respx.mock
async def test_send_manda_mensagem_de_texto_com_o_evento_e_a_mensagem(
    channel: WhatsAppBusinessNotificationChannel,
) -> None:
    route = respx.post(_URL).mock(
        return_value=httpx.Response(200, json={"messages": [{"id": "wamid.fake"}]})
    )

    await channel.send(Notification(event_type="new_checkout", message="Novo pedido: o1"))

    assert route.called
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer fake-access-token-nao-e-real"
    import json

    body = json.loads(request.content)
    assert body["messaging_product"] == "whatsapp"
    assert body["to"] == "5511999999999"
    assert body["type"] == "text"
    assert body["text"]["body"] == "[new_checkout] Novo pedido: o1"


@respx.mock
async def test_send_com_template_configurado_manda_mensagem_de_template(
) -> None:
    channel = WhatsAppBusinessNotificationChannel(
        access_token="fake-access-token-nao-e-real",
        phone_number_id="1234567890",
        recipient_number="5511999999999",
        template_name="pedido_confirmado",
    )
    route = respx.post(_URL).mock(
        return_value=httpx.Response(200, json={"messages": [{"id": "wamid.fake"}]})
    )

    await channel.send(Notification(event_type="new_checkout", message="Novo pedido: o1"))

    assert route.called
    import json

    body = json.loads(route.calls[0].request.content)
    assert body["type"] == "template"
    assert body["template"]["name"] == "pedido_confirmado"
    assert body["template"]["components"][0]["parameters"][0]["text"] == "Novo pedido: o1"


@respx.mock
async def test_send_propaga_erro_da_api_como_httpstatuserror(
    channel: WhatsAppBusinessNotificationChannel,
) -> None:
    respx.post(_URL).mock(
        return_value=httpx.Response(401, json={"error": {"message": "Invalid OAuth access token"}})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await channel.send(Notification(event_type="new_checkout", message="Novo pedido: o1"))
