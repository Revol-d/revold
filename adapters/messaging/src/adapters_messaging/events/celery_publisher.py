"""Adapter real de core_events.ports.EventPublisher — publica via Celery
contra o broker Redis (ADR-0013).

Fica de propósito desacoplado do worker que consome (workers/event-worker):
este módulo nunca importa `event_worker`, só conhece o broker e o *nome* da
tarefa (`event_worker.process_event`) — o mesmo padrão usado por qualquer
produtor/consumidor Celery, e evita que o adapter de publicação precise da
imagem/dependências do worker instaladas.
"""
from __future__ import annotations

import os
from typing import Protocol

from core_events.domain import DomainEvent

_TASK_NAME = "event_worker.process_event"


class _CeleryLike(Protocol):
    """O único método que este adapter precisa da instância Celery — torna
    o adapter testável sem subir um app Celery de verdade (ver
    adapters/messaging/tests/test_celery_publisher.py)."""

    def send_task(self, name: str, kwargs: dict) -> object: ...


class CeleryEventPublisher:
    provider_name = "celery"

    def __init__(self, celery_app: _CeleryLike | None = None) -> None:
        self._app: _CeleryLike = celery_app or _default_celery_app()

    async def publish(self, event: DomainEvent) -> None:
        # send_task é síncrono (só enfileira no broker — um LPUSH no Redis),
        # não há await real aqui; a assinatura é async pra respeitar a porta
        # EventPublisher e permitir um adapter futuro que precise de I/O
        # assíncrono de verdade (ex. um broker HTTP).
        self._app.send_task(_TASK_NAME, kwargs={"event_name": event.name, "payload": event.payload})


def _default_celery_app() -> _CeleryLike:
    from celery import Celery

    return Celery("revold_events_publisher", broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
