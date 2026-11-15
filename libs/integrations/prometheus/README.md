# `revold_prometheus`

Métricas no Prometheus: implementa a porta MetricsPublisher da plataforma.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

`PrometheusMetricsPublisher`: contadores e histogramas em memória do processo, criados sob demanda por nome. Quem os lê é o Prometheus, por scrape do `/metrics` do app (ADR-0017).

## O que NÃO faz

- **Não expõe o endpoint `/metrics`.** Isso é do app.
- **Não decide o que medir.** Quem chama `increment` e `observe` é o app ou o produto, pela porta.

## Testes

```powershell
uv run pytest libs/integrations/prometheus/tests -q
```
