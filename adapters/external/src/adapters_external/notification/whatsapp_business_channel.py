"""Adapter real de core_notification.ports.NotificationChannel via WhatsApp
Business Platform (Meta Cloud API, ADR-0025) — avisa a Nick (não o
cliente) de eventos assíncronos (`checkout.created`, `stock.low`) por
WhatsApp em vez de só e-mail/log.

**Limitação real da própria API, não deste adapter**: fora da janela de
"conversa" de 24h (o destinatário ter mandado mensagem pro número de
teste/produção recentemente), a Meta só aceita mensagem de **template**
pré-aprovado, não texto livre — mandar `type: text` fora da janela falha
com erro da própria API. Este adapter manda `type: text` por padrão
(suficiente para o número de teste, onde a Nick pode iniciar a janela
mandando uma mensagem primeiro) e aceita um `template_name` opcional para
quando houver um template aprovado em produção — ver ADR-0025 para a
decisão completa."""
from __future__ import annotations

import httpx

from core_notification.domain import Notification

_GRAPH_API_VERSION = "v20.0"


class WhatsAppBusinessNotificationChannel:
    provider_name = "whatsapp-business"

    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        recipient_number: str,
        template_name: str | None = None,
    ) -> None:
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._recipient_number = recipient_number
        self._template_name = template_name

    def _build_payload(self, notification: Notification) -> dict:
        if self._template_name:
            # Mensagem de template (ADR-0025) — necessária fora da janela de
            # 24h de conversa. O corpo do template precisa já estar
            # aprovado pela Meta com um parâmetro de texto livre; não dá
            # pra validar isso sem uma conta real (ver ADR-0025).
            return {
                "messaging_product": "whatsapp",
                "to": self._recipient_number,
                "type": "template",
                "template": {
                    "name": self._template_name,
                    "language": {"code": "pt_BR"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": notification.message}],
                        }
                    ],
                },
            }
        return {
            "messaging_product": "whatsapp",
            "to": self._recipient_number,
            "type": "text",
            "text": {"body": f"[{notification.event_type}] {notification.message}"},
        }

    async def send(self, notification: Notification) -> None:
        url = f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{self._phone_number_id}/messages"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self._access_token}"},
                json=self._build_payload(notification),
            )
            response.raise_for_status()
