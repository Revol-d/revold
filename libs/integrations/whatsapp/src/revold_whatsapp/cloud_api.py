"""Cliente da WhatsApp Business Platform (Meta Cloud API, ADR-0025).

**Limitação real da própria API, não deste cliente**: fora da janela de "conversa" de 24h (o
destinatário ter mandado mensagem para o número recentemente), a Meta só aceita mensagem de
**template** pré-aprovado, não texto livre. Mandar `type: text` fora da janela falha com erro da
própria API. Por isso existem os dois envios: `send_text` e `send_template`.
"""

from __future__ import annotations

from typing import Any

import httpx

_GRAPH_API_VERSION = "v20.0"
_DEFAULT_LANGUAGE_CODE = "pt_BR"


def text_payload(*, to: str, body: str) -> dict[str, Any]:
    """Corpo de uma mensagem de texto livre (só vale dentro da janela de 24h)."""
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }


def template_payload(
    *, to: str, template_name: str, body_text: str, language_code: str = _DEFAULT_LANGUAGE_CODE
) -> dict[str, Any]:
    """Corpo de uma mensagem de template, com um parâmetro de texto livre no corpo.

    O template precisa já estar aprovado pela Meta com esse parâmetro; não dá para validar isso
    sem uma conta real (ADR-0025).
    """
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": body_text}],
                }
            ],
        },
    }


class WhatsAppCloudClient:
    """Envia mensagens por um número da WhatsApp Business Platform."""

    def __init__(self, *, access_token: str, phone_number_id: str) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id

    async def send_text(self, *, to: str, body: str) -> None:
        await self._post(text_payload(to=to, body=body))

    async def send_template(self, *, to: str, template_name: str, body_text: str) -> None:
        await self._post(template_payload(to=to, template_name=template_name, body_text=body_text))

    async def _post(self, payload: dict[str, Any]) -> None:
        url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{self._phone_number_id}/messages"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self._access_token}"},
                json=payload,
            )
            response.raise_for_status()
