"""Tarefa Celery genérica que consome eventos publicados por
adapters_messaging.events.celery_publisher.CeleryEventPublisher (ADR-0013).

Só monta as dependências reais (Postgres, o LLMProvider/NotificationChannel
configurados via LLM_PROVIDER/NOTIFICATION_PROVIDER) e chama
event_worker.dispatch, que é quem tem a lógica de verdade (testada com
fakes, sem infraestrutura, em tests/test_dispatch.py). O round-trip
completo — publicar via CeleryEventPublisher, um worker de verdade
consumir esta tarefa contra Redis real — é testado em
tests/test_integration_worker.py (marker `integration`, pula sozinho sem
Redis alcançável).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from celery import Celery

from adapters_external.ai.factory import get_llm_provider
from adapters_external.notification.factory import get_notification_channel
from adapters_messaging.webhooks.factory import get_webhook_sender, get_webhook_urls
from adapters_persistence.ai_assistant.repository import PostgresProductIndexRepository
from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from core_events.domain import DomainEvent

from event_worker import dispatch

logger = logging.getLogger(__name__)

celery_app = Celery(
    "event_worker", broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)

_engine = make_engine()
_session_factory = make_session_factory(_engine)


@celery_app.task(name="event_worker.process_event")
def process_event(event_name: str, payload: dict[str, Any]) -> None:
    asyncio.run(_dispatch(event_name, payload))


async def _dispatch(event_name: str, payload: dict[str, Any]) -> None:
    if event_name == "product.updated":
        llm = get_llm_provider()
        async with _session_factory() as session:
            ok = await dispatch.handle_product_updated(
                payload,
                product_repository=PostgresProductRepository(session),
                llm=llm,
                index=PostgresProductIndexRepository(session),
            )
        if not ok:
            logger.info(
                "product.updated para SKU %r ignorado: produto não existe mais",
                payload.get("sku"),
            )
    elif event_name == "checkout.created":
        await dispatch.handle_checkout_created(
            payload, notification_channel=get_notification_channel()
        )
    elif event_name == "stock.low":
        await dispatch.handle_stock_low(payload, notification_channel=get_notification_channel())
    else:
        # Evento sem handler registrado ainda não é um erro — é
        # extensibilidade: um core pode começar a publicar um evento novo
        # antes do handler correspondente existir (ex. rollout gradual).
        logger.warning("evento %r recebido sem handler registrado, ignorado", event_name)

    # Encaminhamento para webhooks de parceiro (ADR-0016) — best-effort,
    # depois do processamento interno já ter acontecido; lista vazia
    # (nenhum parceiro configurado via WEBHOOK_URLS) é o caso comum e não
    # faz nenhuma chamada de rede.
    webhook_urls = get_webhook_urls()
    if webhook_urls:
        results = await dispatch.forward_to_webhooks(
            DomainEvent(name=event_name, payload=payload),
            webhook_urls=webhook_urls,
            sender=get_webhook_sender(),
        )
        for url, delivered in results.items():
            if not delivered:
                logger.warning("webhook para %r não confirmou entrega de %r", url, event_name)
