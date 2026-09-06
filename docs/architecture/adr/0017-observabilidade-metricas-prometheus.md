# ADR-0017: Observabilidade — métricas (Prometheus/Grafana)

**Status:** Aceito

## Contexto

O `Readme.md` cita observabilidade (Azure Monitor/App Insights/Sentinel/Prometheus/Grafana) como parte da visão de stack da empresa — nunca implementada (achado da avaliação macro anterior, ver `status-implementacao.md`). Nenhum código de métrica existia: sem contador de requisição, sem histograma de latência, sem visibilidade de quantos checkouts ou quantos alertas de estoque baixo acontecem por dia.

Métricas são Categoria A do `planejamento-leafs-e-adaptadores.md` — 100% real hoje, zero credencial: Prometheus/Grafana são serviços self-hosted, o cliente (`prometheus_client`) só acumula contadores no processo do próprio `api-gateway`.

## Decisão

**Porta pequena e centralizada, core novo**: `core-observability` (mesmo raciocínio do `core-events`, ADR-0013 — melhor um formato único de instrumentação do que cada módulo inventar seu próprio jeito de contar/medir e acabar com nome de métrica divergente para "a mesma coisa"):

```python
class MetricsPublisher(Protocol):
    def increment(self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None) -> None: ...
    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None: ...
```

- **`PrometheusMetricsPublisher`** (`adapters/external`): usa `prometheus_client` (`Counter`/`Histogram`), cacheando o objeto métrica por nome (criar duas vezes o mesmo nome no mesmo registry levanta erro). Registry próprio (não o global do processo) — isolado, sem efeito colateral em nenhum outro código que porventura use `prometheus_client` diretamente.
- **`api_gateway.dependencies.get_metrics_publisher`**: singleton de processo (não um por requisição — um `Counter`/`Histogram` precisa acumular entre chamadas, senão cada scrape veria os contadores zerados).
- **Middleware HTTP genérico** (`api_gateway.main`): incrementa `http_requests_total` e observa `http_request_duration_seconds`, com labels `method`+`status` para toda requisição — **deliberadamente sem label de path**, para não arriscar explosão de cardinalidade num endpoint com SKU na URL (`/api/catalog/products/{sku}`); cada SKU viraria uma série nova. `/health` e o próprio `/metrics` são excluídos da contagem (ruído autoreferente / tráfego de healthcheck, não tráfego de negócio real).
- **Métricas de negócio pontuais**: `checkout_created_total` (incrementado em `POST /api/cart/{id}/checkout`) e `stock_low_total` (incrementado em `api_gateway.orchestration.notify_if_low_stock`, que já é o ponto único compartilhado entre `cart.py` e `inventory.py` — `metrics` é um parâmetro opcional aí de propósito, para não obrigar todo teste existente de cart/inventory a passar um fake de métricas só para continuar funcionando).
- **`GET /metrics`**: endpoint de scrape, formato de exposição padrão do Prometheus, sem autenticação (convenção usual — fica atrás da rede interna do compose).
- **`docker-compose.yml`**: serviços `prometheus` (config em `docker/prometheus/prometheus.yml`, faz scrape do `api-gateway:8000/metrics` a cada 15s) e `grafana` (porta `3002`, anônimo habilitado como Viewer — só dev local).

## Testes

- `adapters/external/tests/test_prometheus_metrics_publisher.py`: `increment`/`observe` com e sem labels, reuso do mesmo nome, formato de exposição via `generate_latest`.
- `apps/api-gateway/tests/test_metrics_endpoint.py`: `/metrics` expõe os contadores; `/health` e o próprio `/metrics` não entram na contagem (comparação antes/depois); uma requisição real incrementa o contador certo (`method`+`status`).

## Consequências

- Nenhuma credencial nova — Prometheus/Grafana são só mais dois serviços Docker, mesma categoria de Postgres/Redis.
- Cardinalidade controlada de propósito: sem label de path no contador genérico. Um dashboard por rota específica, se algum dia fizer sentido, precisaria de instrumentação pontual (como `checkout_created_total`), não do middleware genérico.
- Base pronta para qualquer projeto futuro do framework — `MetricsPublisher` é a porta única, sem reimplementar em cada módulo.
