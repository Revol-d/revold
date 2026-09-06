from __future__ import annotations

from prometheus_client import generate_latest

from adapters_external.observability.prometheus_metrics_publisher import (
    PrometheusMetricsPublisher,
)


def _exposition_text(publisher: PrometheusMetricsPublisher) -> str:
    return generate_latest(publisher.registry).decode("utf-8")


def test_increment_sem_labels_aparece_na_exposicao() -> None:
    publisher = PrometheusMetricsPublisher()

    publisher.increment("checkout_created_total")
    publisher.increment("checkout_created_total")

    text = _exposition_text(publisher)
    assert "checkout_created_total 2.0" in text


def test_increment_com_value_customizado() -> None:
    publisher = PrometheusMetricsPublisher()

    publisher.increment("itens_processados_total", value=5.0)

    text = _exposition_text(publisher)
    assert "itens_processados_total 5.0" in text


def test_increment_com_labels_particiona_contadores() -> None:
    publisher = PrometheusMetricsPublisher()

    publisher.increment("http_requests_total", labels={"method": "GET", "status": "200"})
    publisher.increment("http_requests_total", labels={"method": "GET", "status": "200"})
    publisher.increment("http_requests_total", labels={"method": "POST", "status": "500"})

    text = _exposition_text(publisher)
    assert 'method="GET",status="200"} 2.0' in text
    assert 'method="POST",status="500"} 1.0' in text


def test_observe_registra_no_histograma() -> None:
    publisher = PrometheusMetricsPublisher()

    publisher.observe("http_request_duration_seconds", 0.25)
    publisher.observe("http_request_duration_seconds", 0.75)

    text = _exposition_text(publisher)
    assert "http_request_duration_seconds_count 2.0" in text
    assert "http_request_duration_seconds_sum 1.0" in text


def test_mesmo_nome_reusa_a_metrica_ja_criada() -> None:
    publisher = PrometheusMetricsPublisher()

    publisher.increment("chamadas_total")
    publisher.increment("chamadas_total")
    publisher.increment("chamadas_total")

    text = _exposition_text(publisher)
    assert "chamadas_total 3.0" in text
