# ADR-0013: core-events e barramento de eventos (Celery/Redis)

**Status:** Aceito

## Contexto

Duas lacunas concretas, achadas ao planejar como enriquecer o framework enquanto credenciais reais (Azure AD, Google, WhatsApp Business API, Azure OpenAI real) seguem indisponíveis:

1. Editar um produto no admin não atualiza o índice vetorial de IA (RAG) — só um clique manual em "reindexar tudo" (`POST /api/assistant/reindex`) faz isso, e reindexa o catálogo inteiro, não só o produto editado.
2. `NotifyNewCheckout`/`NotifyLowStock` (core-notification) eram chamados **de forma síncrona, dentro da requisição HTTP** (`api_gateway.routers.cart`/`inventory`). Se o canal de notificação falhar ou demorar, isso não deveria travar nem falhar o checkout ou a reserva de estoque — mas do jeito que estava, um erro ali propagava para a resposta HTTP do cliente.

`workers/catalog-indexer` já tinha Celery com broker Redis configurado, mas o próprio código admitia: *"não testado com um worker Celery de verdade nesta sessão... precisaria de Redis e um worker rodando, que este ambiente não tem"*. O `docker-compose.yml` já tem o serviço `redis` (usado para sessão, ADR-0010) — não faltava credencial nenhuma pra validar isso de verdade, faltava ligar os pontos.

## Decisão

Um core novo, pequeno, central: **core-events**. A alternativa considerada — cada core publicar seu próprio formato de evento ad-hoc — foi descartada de propósito: sem um formato e um ponto de publicação centralizados, dois cores publicando o "mesmo" acontecimento de jeitos diferentes leva a handler duplicado, consumo divergente entre workers, e problema de deduplicação (o mesmo checkout notificado duas vezes por dois caminhos diferentes). Centralizar em `core_events.domain.DomainEvent` + `core_events.ports.EventPublisher` resolve isso na raiz: um único formato, um único ponto de publicação, um único worker consumidor.

- **`DomainEvent`** (`name: str`, `payload: dict`): `name` segue a convenção `<contexto>.<acontecimento>` (`product.updated`, `checkout.created`, `stock.low`).
- **`EventPublisher`** (porta): `publish(event) -> None`.
- **`InMemoryEventPublisher`** (`adapters/messaging`, dev/default): loga e guarda em memória, sem consumidor real — o sistema continua funcionando sem Redis/worker, só sem o efeito assíncrono.
- **`CeleryEventPublisher`** (`adapters/messaging`, real): publica via `send_task` contra o broker Redis, **sem nunca importar o worker** — desacoplamento de propósito (produtor só precisa do broker e do nome da tarefa).
- **`workers/event-worker`**: consome `event_worker.process_event`, roteando por `event_name` para `event_worker.dispatch` (lógica pura, testada com fakes) — hoje trata `product.updated` (reindexação incremental via `catalog_indexer.reindex.reindex_one_product`, novo), `checkout.created` e `stock.low` (ambos via `core_notification.use_cases`, reaproveitando o que já existia).

Seleção via env var `EVENT_PUBLISHER` (`memory` por padrão, `celery` quando configurado — ver `api_gateway.dependencies.get_event_publisher`), mesmo padrão de `LLM_PROVIDER`/`AUTH_PROVIDER`.

## Testes

- `cores/core-events/tests`: validação do `DomainEvent` (nome vazio, convenção `<contexto>.<acontecimento>`, imutabilidade).
- `adapters/messaging/tests/test_celery_publisher.py`: `CeleryEventPublisher.publish` enfileira a tarefa certa com os kwargs certos — via stub, sem broker real.
- `workers/event-worker/tests/test_dispatch.py`: lógica de cada handler, com fakes — sem Celery/Redis/Postgres.
- `workers/event-worker/tests/test_celery_app_routing.py`: roteamento por `event_name` dentro de `event_worker.celery_app._dispatch` — com fakes, sem infraestrutura.
- `workers/event-worker/tests/test_integration_worker.py` (`@pytest.mark.integration`): **round-trip real** — publica contra Redis de verdade, sobe um worker Celery de verdade em subprocesso, confirma que o handler rodou (via saída do worker). Fecha a lacuna que estava documentada como não testada. Pula sozinho se Redis não estiver alcançável.

## Consequências

- Novo serviço `worker` no `docker-compose.yml` (mesma imagem do `api-gateway`, comando diferente).
- `api_gateway.routers.cart`/`inventory` não conhecem mais `NotificationChannel` diretamente — só `EventPublisher`. Quem de fato envia a notificação roda assíncrono, fora do caminho de requisição HTTP.
- `api_gateway.orchestration.notify_if_low_stock` passou a publicar evento em vez de chamar o canal diretamente.
- Testes de `test_cart_routes.py`/`test_inventory_routes.py`/`test_inventory_rbac.py` passaram a verificar o evento publicado (`fake_event_publisher.published`), não mais o canal de notificação — a notificação em si é responsabilidade do worker, testada em `workers/event-worker/tests`.
- Base pronta para qualquer evento futuro (novo core, novo handler) sem inventar um novo mecanismo de transporte a cada vez.
