"""Teste de integração real do round-trip completo: publica um evento via
CeleryEventPublisher contra Redis de verdade, sobe um worker Celery de
verdade (subprocesso, consumindo event_worker.celery_app) e confirma que o
handler rodou de fato.

Fecha uma lacuna que estava documentada há tempo no código deste monorepo
(workers/catalog-indexer/src/catalog_indexer/celery_app.py dizia "não
testado com um worker Celery de verdade nesta sessão... precisaria de
Redis e um worker rodando") — Redis já está disponível neste ambiente
(usado para sessão, ADR-0010), então este teste valida a entrega de
verdade em vez de só a lógica de despacho com fakes (ver test_dispatch.py).

Pula sozinho se Redis não estiver alcançável (mesma convenção dos testes
de integração contra Postgres real — ver
adapters/persistence/tests/test_catalog_repository_integration.py).
Usa checkout.created/stock.low (não product.updated) de propósito: os
dois passam pelo LoggingNotificationChannel, que não precisa de Postgres
nem de credencial nenhuma — mantém este teste focado em validar só o
transporte Celery+Redis, não a lógica de negócio (já coberta por
test_dispatch.py).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.integration

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _redis_reachable() -> bool:
    try:
        import redis as redis_sync

        client = redis_sync.from_url(REDIS_URL, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def worker_process():
    if not _redis_reachable():
        pytest.skip(f"Redis não alcançável em {REDIS_URL} — pulando teste de integração.")

    env = {**os.environ, "REDIS_URL": REDIS_URL, "NOTIFICATION_PROVIDER": "logging"}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "event_worker.celery_app",
            "worker",
            "--loglevel=info",
            "--concurrency=1",
            "--without-heartbeat",
            "--without-mingle",
            "--without-gossip",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _wait_for_worker_ready(proc, timeout=15)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _wait_for_worker_ready(proc: subprocess.Popen, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("worker Celery encerrou antes de ficar pronto")
        # celery imprime "ready." no banner de inicialização quando conecta no broker
        line = proc.stdout.readline()
        if "ready" in line.lower():
            return
    raise TimeoutError("worker Celery não ficou pronto a tempo")


def _wait_for_log_line(proc: subprocess.Popen, *, contains: str, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    collected = ""
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        collected += line
        if contains in line:
            return collected
    raise AssertionError(
        f"não achei {contains!r} na saída do worker em {timeout}s. Saída coletada:\n{collected}"
    )


async def test_publica_checkout_created_e_worker_real_processa(worker_process) -> None:
    from adapters_messaging.events.celery_publisher import CeleryEventPublisher
    from core_events.domain import DomainEvent

    publisher = CeleryEventPublisher()
    await publisher.publish(
        DomainEvent(name="checkout.created", payload={"cart_id": "c-integration-1", "summary_text": "1x Camiseta Azul"})
    )

    output = _wait_for_log_line(worker_process, contains="c-integration-1", timeout=15)
    assert "new_checkout" in output


async def test_publica_stock_low_e_worker_real_processa(worker_process) -> None:
    from adapters_messaging.events.celery_publisher import CeleryEventPublisher
    from core_events.domain import DomainEvent

    publisher = CeleryEventPublisher()
    await publisher.publish(
        DomainEvent(name="stock.low", payload={"sku": "SKU-INTEGRATION", "quantity_available": 1, "threshold": 5})
    )

    output = _wait_for_log_line(worker_process, contains="SKU-INTEGRATION", timeout=15)
    assert "low_stock" in output
