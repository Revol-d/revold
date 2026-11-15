"""Adapter de desenvolvimento de revold_platform.events.ports.WebhookSender — só loga,
sem chamada de rede nenhuma (ADR-0016). Default enquanto nenhum
parceiro/integração real tem um endpoint registrado."""
from __future__ import annotations

import logging

from revold_platform.events.domain import DomainEvent

_logger = logging.getLogger(__name__)


class LoggingWebhookSender:
    provider_name = "logging"

    def __init__(self) -> None:
        self.sent: list[tuple[str, DomainEvent]] = []

    async def send(self, url: str, event: DomainEvent) -> bool:
        self.sent.append((url, event))
        _logger.info("webhook (dev, não enviado de verdade): url=%s evento=%s", url, event.name)
        return True
