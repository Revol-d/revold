# `revold_messaging`

Entrega de eventos para fora do processo: fila (Celery) e webhook HTTP.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `platform`

## O que faz

- `celery_publisher.CeleryEventPublisher`: publica o evento no broker para o `event-worker` consumir (ADR-0013);
- `http_webhook_sender.HttpWebhookSender`: entrega o evento a um endpoint de parceiro, com retentativa e backoff (ADR-0016);
- `webhook_factory.build_webhook_sender(provider)`: escolhe entre o envio HTTP e o de log.

## O que NÃO faz

- **Não consome evento.** Quem consome é o app `event-worker`.
- **Não define o formato do evento.** `DomainEvent` e as portas são de `revold_platform.events`.

## Testes

```powershell
uv run pytest libs/integrations/messaging/tests -q
```
