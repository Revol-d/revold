"""Adapter real de revold_notification.ports.NotificationChannel via WhatsApp
Business Platform (Meta Cloud API, ADR-0025) — avisa a Nick (não o
cliente) de eventos assíncronos (`checkout.created`, `stock.low`) por
WhatsApp em vez de só e-mail/log.

Este adapter decide o que dizer e por qual tipo de mensagem. Quem fala com a
API é o cliente `revold_whatsapp.cloud_api.WhatsAppCloudClient`
(libs/integrations/whatsapp).

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

from revold_notification.domain import Notification
from revold_whatsapp.cloud_api import WhatsAppCloudClient


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
        self._client = WhatsAppCloudClient(
            access_token=access_token, phone_number_id=phone_number_id
        )
        self._recipient_number = recipient_number
        self._template_name = template_name

    async def send(self, notification: Notification) -> None:
        if self._template_name:
            # Mensagem de template (ADR-0025) — necessária fora da janela de
            # 24h de conversa. O corpo do template precisa já estar
            # aprovado pela Meta com um parâmetro de texto livre.
            await self._client.send_template(
                to=self._recipient_number,
                template_name=self._template_name,
                body_text=notification.message,
            )
            return
        await self._client.send_text(
            to=self._recipient_number,
            body=f"[{notification.event_type}] {notification.message}",
        )
