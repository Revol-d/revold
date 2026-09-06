"""Ponto de entrada FastAPI do api-gateway.

Composição: monta os routers de cada core que já expõe API HTTP. Hoje
core-catalog, core-cart e core-inventory; os demais cores entram aqui
conforme forem implementados.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api_gateway.dependencies import get_metrics_publisher, get_metrics_registry
from api_gateway.routers.assistant import router as assistant_router
from api_gateway.routers.cart import router as cart_router
from api_gateway.routers.catalog import router as catalog_router
from api_gateway.routers.identity import router as identity_router
from api_gateway.routers.inventory import router as inventory_router
from api_gateway.routers.public_api import router as public_api_router

app = FastAPI(
    title="Revold API Gateway",
    description="Composição das APIs HTTP dos cores do monorepo revold.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # localhost:3000 = storefront, localhost:3001 = admin-dashboard (RBAC
    # STAFF/ADMIN, ver ADR-0010).
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(identity_router)
app.include_router(inventory_router)
app.include_router(assistant_router)
app.include_router(public_api_router)

# Serve os arquivos gravados por LocalFilesystemStorage (ADR-0015, adapter
# de dev de core_catalog.ports.MediaStorage) — sem efeito quando
# MEDIA_STORAGE_PROVIDER=azure-blob (o diretório simplesmente fica vazio).
_media_dir = Path(os.environ.get("MEDIA_STORAGE_LOCAL_DIR", "/app/media"))
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

# Caminhos que não entram na contagem de http_requests_total: /metrics é o
# próprio scrape do Prometheus (contá-lo criaria ruído autoreferente) e
# /health é chamado a cada poucos segundos pelo healthcheck do Docker
# Compose — nenhum dos dois é tráfego de negócio real (ADR-0017).
_METRICS_EXCLUDED_PATHS = frozenset({"/metrics", "/health"})


@app.middleware("http")
async def _metrics_middleware(request: Request, call_next):
    if request.url.path in _METRICS_EXCLUDED_PATHS:
        return await call_next(request)

    metrics = get_metrics_publisher()
    start = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - start

    labels = {"method": request.method, "status": str(response.status_code)}
    metrics.increment("http_requests_total", labels=labels)
    metrics.observe("http_request_duration_seconds", duration_seconds, labels=labels)
    return response


@app.get("/metrics")
async def metrics() -> Response:
    """Endpoint de scrape do Prometheus (ADR-0017) — formato de exposição
    padrão, sem autenticação (mesma convenção usual desse endpoint: fica
    atrás da rede interna, nunca exposto publicamente)."""
    return Response(content=generate_latest(get_metrics_registry()), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
