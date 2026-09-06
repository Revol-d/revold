"""Implementação real (Prometheus) da porta
core_observability.ports.MetricsPublisher (ADR-0017). 100% real hoje, zero
credencial — `prometheus_client` só mantém contadores em memória do próprio
processo; quem os lê é o serviço Prometheus (docker-compose), fazendo
scrape do endpoint `/metrics`.

`Counter`/`Histogram` do prometheus_client precisam ser criados uma única
vez por nome (criar duas vezes o mesmo nome no mesmo registry levanta
ValueError) — por isso o adapter guarda um cache por nome, criando sob
demanda na primeira vez que aquela métrica é usada.
"""
from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram


class PrometheusMetricsPublisher:
    provider_name = "prometheus"

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self._registry = registry if registry is not None else CollectorRegistry()
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}

    @property
    def registry(self) -> CollectorRegistry:
        return self._registry

    def increment(
        self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        labels = labels or {}
        counter = self._counters.get(name)
        if counter is None:
            counter = Counter(
                name, f"revold: {name}", labelnames=sorted(labels.keys()), registry=self._registry
            )
            self._counters[name] = counter
        (counter.labels(**labels) if labels else counter).inc(value)

    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        labels = labels or {}
        histogram = self._histograms.get(name)
        if histogram is None:
            histogram = Histogram(
                name, f"revold: {name}", labelnames=sorted(labels.keys()), registry=self._registry
            )
            self._histograms[name] = histogram
        (histogram.labels(**labels) if labels else histogram).observe(value)
