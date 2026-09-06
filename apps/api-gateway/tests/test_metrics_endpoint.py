"""Teste do endpoint /metrics e do middleware de instrumentação HTTP
(ADR-0017) — sobe o app FastAPI de verdade; a métrica em si vive no
registry privado do singleton PrometheusMetricsPublisher (ver
api_gateway.dependencies), então não precisa de nenhum override de
dependência para este teste."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_metrics_endpoint_expoe_contadores_http(client: AsyncClient) -> None:
    # gera pelo menos uma requisição contável antes de checar
    await client.get("/api/catalog/products")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


def _http_requests_total_lines(text: str) -> list[str]:
    return sorted(line for line in text.splitlines() if line.startswith("http_requests_total{"))


async def test_health_nao_conta_como_trafego_instrumentado(client: AsyncClient) -> None:
    before = (await client.get("/metrics")).text

    for _ in range(3):
        health_response = await client.get("/health")
        assert health_response.status_code == 200

    after = (await client.get("/metrics")).text

    assert _http_requests_total_lines(before) == _http_requests_total_lines(after)


async def test_metrics_scrape_nao_conta_a_si_mesmo(client: AsyncClient) -> None:
    before = (await client.get("/metrics")).text

    for _ in range(3):
        await client.get("/metrics")

    after = (await client.get("/metrics")).text

    assert _http_requests_total_lines(before) == _http_requests_total_lines(after)


async def test_requisicao_real_incrementa_o_contador_com_method_e_status(
    client: AsyncClient,
) -> None:
    # /api/auth/login/start não toca Postgres nem Redis (DevIdentityProvider
    # é síncrono e sem estado) — evita o problema conhecido de reusar uma
    # engine assíncrona criada uma vez entre event loops diferentes por
    # teste, que aconteceria com qualquer endpoint que use get_db_session
    # neste arquivo (que não sobrescreve essa dependência com fake).
    before_text = (await client.get("/metrics")).text
    before_count = _extract_count(before_text, method="POST", status="200")

    response = await client.post(
        "/api/auth/login/start", json={"redirect_uri": "http://localhost:3000/callback"}
    )
    assert response.status_code == 200

    after_text = (await client.get("/metrics")).text
    after_count = _extract_count(after_text, method="POST", status="200")

    assert after_count == before_count + 1


def _extract_count(text: str, *, method: str, status: str) -> float:
    target = f'method="{method}",status="{status}"'
    for line in text.splitlines():
        if line.startswith("http_requests_total{") and target in line:
            return float(line.rsplit(" ", 1)[-1])
    return 0.0
