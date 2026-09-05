"""Adapter de desenvolvimento do NotificationChannel (core-notification).

Não fala com nenhum serviço externo: registra a notificação no log
estruturado do processo e guarda uma cópia em memória (útil em teste e,
futuramente, para um endpoint de admin listar o histórico recente). Nunca
deve ser a única forma de aviso em produção — é um stand-in até existir
WhatsApp Business API (aprovação da Meta pendente) ou um serviço de e-mail
configurado. Trocar por um canal real é só trocar o que a dependency do
api-gateway devolve; a porta (NotificationChannel) não muda.
"""
from __future__ import annotations

import logging

from core_notification.domain import Notification

logger = logging.getLogger("revold.notifications")


class LoggingNotificationChannel:
    provider_name = "logging"

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        logger.info("[%s] %s", notification.event_type, notification.message)
        self.sent.append(notification)
