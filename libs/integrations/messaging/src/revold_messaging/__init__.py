"""Entrega de eventos para fora do processo: fila (Celery) e webhook HTTP.

Implementa as portas de `revold_platform.events.ports`:

- `celery_publisher.CeleryEventPublisher`: publica o evento no broker, para o `event-worker`
  consumir (ADR-0013);
- `http_webhook_sender.HttpWebhookSender`: entrega o evento a um endpoint de parceiro, com
  retentativa (ADR-0016);
- `webhook_factory.build_webhook_sender`: escolhe entre o envio HTTP e o de log.

Os adapters que não falam com sistema nenhum (`InMemoryEventPublisher`, `LoggingWebhookSender`)
moram em `revold_platform.events`.
"""

__all__ = ["celery_publisher", "http_webhook_sender", "webhook_factory"]
