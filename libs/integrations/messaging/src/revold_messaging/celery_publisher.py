"""Adapter real de revold_platform.events.ports.EventPublisher — publica via Celery
contra o broker Redis (ADR-0013).

Fica de propósito desacoplado do worker que consome (apps/ecommerce/event-worker):
este módulo nunca importa `event_worker`, só conhece o broker e o *nome* da
tarefa (`event_worker.process_event`) — o mesmo padrão usado por qualquer
produtor/consumidor Celery, e evita que o adapter de publicação precise da
imagem/dependências do worker instaladas.
"""
from __future__ import annotations

from typing import Protocol

from revold_platform.events.domain import DomainEvent

_TASK_NAME = "event_worker.process_event"


class _CeleryLike(Protocol):
    """O único método que este adapter precisa da instância Celery — torna
    o adapter testável sem subir um app Celery de verdade (ver
    libs/integrations/messaging/tests/test_celery_publisher.py)."""

    def send_task(self, name: str, kwargs: dict) -> object: ...


class CeleryEventPublisher:
    provider_name = "celery"

    def __init__(self, celery_app: _CeleryLike | None = None, *, broker_url: str | None = None) -> None:
        """Recebe um app Celery pronto ou a URL do broker.

        A URL vem do `settings.py` do app: este módulo não lê o ambiente.
        """
        if celery_app is None:
            if not broker_url:
                raise ValueError("CeleryEventPublisher precisa de `celery_app` ou de `broker_url`.")
            celery_app = _make_celery_app(broker_url)
        self._app: _CeleryLike = celery_app

    async def publish(self, event: DomainEvent) -> None:
        # send_task é síncrono (só enfileira no broker — um LPUSH no Redis),
        # não há await real aqui; a assinatura é async pra respeitar a porta
        # EventPublisher e permitir um adapter futuro que precise de I/O
        # assíncrono de verdade (ex. um broker HTTP).
        self._app.send_task(_TASK_NAME, kwargs={"event_name": event.name, "payload": event.payload})


def _make_celery_app(broker_url: str) -> _CeleryLike:
    from celery import Celery

    return Celery("revold_events_publisher", broker=broker_url)
