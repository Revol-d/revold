# `event_worker`

Worker Celery que consome os eventos de domínio da loja (composition root).

- **Tipo:** app · **Runtime:** celery-worker · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `ai-assistant`, `catalog`, `ecommerce`, `messaging`, `notification`, `platform`, `postgres`

## O que faz

Registra a tarefa `event_worker.process_event`, monta os adapters reais e chama os handlers do produto (`revold_ecommerce.application.event_handlers`). Depois encaminha o evento aos webhooks de parceiro configurados. `settings.py` é o único módulo que lê o ambiente.

## O que NÃO faz

- **Não decide o que fazer com o evento.** A regra de cada handler mora no produto e é testada lá.
- **Não publica evento.** Quem publica é o api-gateway, pelo `CeleryEventPublisher`.

## Testes

```powershell
uv run pytest apps/ecommerce/event-worker/tests -q
```
