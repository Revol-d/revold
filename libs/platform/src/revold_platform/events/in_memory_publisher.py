"""Adapter de desenvolvimento/teste para revold_platform.events.ports.EventPublisher.

Não fala com broker nenhum — só loga e guarda em `self.published`, para
quem estiver testando (ou rodando localmente sem Redis) inspecionar o que
foi publicado. É o equivalente, para eventos, do
`revold_notification.adapters.logging_channel.LoggingNotificationChannel`.

Usado como default em `api_gateway.dependencies` quando `EVENT_PUBLISHER`
não está setado para "celery" — nesse modo, eventos são aceitos e
logados, mas NENHUM handler roda (reindexação incremental e notificação
assíncrona não acontecem) até trocar para o adapter Celery real.
"""
from __future__ import annotations

import logging

from revold_platform.events.domain import DomainEvent

logger = logging.getLogger(__name__)


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        logger.info("evento publicado (in-memory, sem consumidor real): %s %s", event.name, event.payload)
