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
- **Dashboard "Revold — Visão Geral" provisionado como código** (adição posterior a este ADR, mesma decisão — fechando a lacuna que a seção de Consequências abaixo já deixava registrada como pendente): `docker/grafana/provisioning/` tem um datasource (`datasources/prometheus.yml`, aponta para `http://prometheus:9090`, uid fixo `prometheus`) e um provider de dashboard (`dashboards/dashboards.yml`, recarrega a cada 30s qualquer `.json` em `dashboards/json/`). `dashboards/json/revold-overview.json` é o dashboard em si — 3 seções (linhas), cada uma no mesmo agrupamento usado no restante da documentação ("checkout / estoque baixo / latência de API"):
  - **Checkout**: taxa de `checkout_created_total` por minuto (série temporal) + total acumulado (stat).
  - **Estoque baixo**: taxa de `stock_low_total` por minuto (série temporal) + total acumulado (stat).
  - **API**: requisições por status (`sum by (status) (rate(http_requests_total[5m]))`), taxa de erro 5xx sobre o total, e latência p50/p95/p99 via `histogram_quantile` sobre `http_request_duration_seconds_bucket`.
  `docker-compose.yml` monta `./docker/grafana/provisioning:/etc/grafana/provisioning:ro` no serviço `grafana` — o dashboard já existe no primeiro load de `make dev`, sem passo manual de "Configuration > Data Sources" nem import de JSON pela UI.

## Testes

- `adapters/external/tests/test_prometheus_metrics_publisher.py`: `increment`/`observe` com e sem labels, reuso do mesmo nome, formato de exposição via `generate_latest`.
- `apps/api-gateway/tests/test_metrics_endpoint.py`: `/metrics` expõe os contadores; `/health` e o próprio `/metrics` não entram na contagem (comparação antes/depois); uma requisição real incrementa o contador certo (`method`+`status`).

## Consequências

- Nenhuma credencial nova — Prometheus/Grafana são só mais dois serviços Docker, mesma categoria de Postgres/Redis.
- Cardinalidade controlada de propósito: sem label de path no contador genérico. Um dashboard por rota específica, se algum dia fizer sentido, precisaria de instrumentação pontual (como `checkout_created_total`), não do middleware genérico.
- Base pronta para qualquer projeto futuro do framework — `MetricsPublisher` é a porta única, sem reimplementar em cada módulo.
- **Dashboard provisionado como arquivo versionado, não como estado só dentro do container Grafana** — `grafana_data` (volume Docker) ainda existe e continua guardando o que for editado na UI, mas a fonte de verdade do dashboard "Revold — Visão Geral" é o `.json` no repositório: `docker compose down -v` (que apaga o volume) não perde o dashboard, e qualquer ajuste feito na UI (`allowUiUpdates: true`) é sobrescrito pelo arquivo do repositório no próximo reload do provider (30s) — quem editar via UI precisa levar a mudança de volta pro `.json` para ela persistir de verdade.
- Consultas do dashboard assumem Prometheus como única fonte (`isDefault: true`, uid fixo `prometheus`) — se um dia houver mais de um datasource, os `uid` fixos no `.json` do dashboard precisam ser revistos.
