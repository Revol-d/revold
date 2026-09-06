"""Porta (interface) que core-events espera que a infraestrutura implemente.

Qualquer adapter (Celery contra Redis real, um publisher em memória para
dev/teste) implementa este Protocol. core-events nunca importa Celery nem
nenhum broker diretamente.
"""
from __future__ import annotations

from typing import Protocol

from core_events.domain import DomainEvent


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None:
        """Publica o evento para consumo assíncrono. Não garante que o
        consumidor já processou quando o método retorna — só que o evento
        foi aceito pelo broker (ou, no adapter em memória, registrado)."""
        ...


class WebhookSender(Protocol):
    """Porta de entrega de evento para um destino HTTP externo — um
    parceiro/integração que se inscreveu para ser avisado de eventos do
    domínio (ADR-0016), diferente de EventPublisher (que alimenta o
    consumidor interno, event-worker). Quem implementa cuida de
    retry/backoff internamente: o chamador só sabe se, no fim, a entrega
    teve sucesso ou não — nunca precisa saber quantas tentativas houve."""

    async def send(self, url: str, event: DomainEvent) -> bool:
        """True se o destino aceitou a entrega (2xx) em alguma tentativa,
        False se todas as tentativas de retry se esgotaram."""
        ...
