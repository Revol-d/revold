"""Porta que qualquer backend de métricas (Prometheus real, fake em
memória para teste) implementa. core-observability nunca importa
prometheus_client diretamente — só quem implementa a porta (ver
adapters_external.observability, ADR-0017).
"""
from __future__ import annotations

from typing import Protocol


class MetricsPublisher(Protocol):
    def increment(
        self, name: str, *, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Incrementa um contador (ex. número de checkouts criados)."""
        ...

    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
        """Registra uma observação num histograma (ex. duração de uma
        requisição, em segundos)."""
        ...
