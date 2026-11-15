"""Testa CeleryEventPublisher sem precisar de um broker de verdade — só
verifica que `send_task` é chamado com o nome de tarefa e os kwargs
corretos, usando um stub que implementa o único método que o adapter
precisa (`_CeleryLike`). O round-trip completo contra um worker Celery de
verdade (com Redis real) é testado em
apps/ecommerce/event-worker/tests/test_integration_worker.py (marker
`integration`)."""
from __future__ import annotations

from revold_messaging.celery_publisher import CeleryEventPublisher
from revold_platform.events.domain import DomainEvent


class _StubCeleryApp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send_task(self, name: str, kwargs: dict) -> None:
        self.sent.append((name, kwargs))


async def test_publish_enfileira_tarefa_com_nome_e_kwargs_corretos() -> None:
    stub = _StubCeleryApp()
    publisher = CeleryEventPublisher(celery_app=stub)

    await publisher.publish(DomainEvent(name="product.updated", payload={"sku": "CAM-001"}))

    assert stub.sent == [
        ("event_worker.process_event", {"event_name": "product.updated", "payload": {"sku": "CAM-001"}})
    ]


async def test_publish_de_multiplos_eventos_acumula_no_broker() -> None:
    stub = _StubCeleryApp()
    publisher = CeleryEventPublisher(celery_app=stub)

    await publisher.publish(DomainEvent(name="checkout.created", payload={"cart_id": "c1"}))
    await publisher.publish(DomainEvent(name="stock.low", payload={"sku": "A"}))

    assert [name for name, _ in stub.sent] == [
        "event_worker.process_event",
        "event_worker.process_event",
    ]
    assert [kwargs["event_name"] for _, kwargs in stub.sent] == ["checkout.created", "stock.low"]
