"""Tarefa Celery genérica que consome eventos publicados por
revold_messaging.celery_publisher.CeleryEventPublisher (ADR-0013).

Só monta as dependências reais (Postgres, o LLMProvider/NotificationChannel
configurados via LLM_PROVIDER/NOTIFICATION_PROVIDER) e chama
revold_ecommerce.application.event_handlers, que é quem tem a lógica de
verdade (testada com fakes, sem infraestrutura, em
products/ecommerce/tests/test_event_handlers.py). O round-trip completo —
publicar via CeleryEventPublisher, um worker de verdade consumir esta tarefa
contra Redis real — é testado em tests/test_integration_worker.py (marker
`integration`, pula sozinho sem Redis alcançável).

A configuração vem de `event_worker.settings`, o único módulo do app que lê
o ambiente.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery import Celery

from event_worker import settings
from revold_ai_assistant.adapters.llm.factory import build_llm_provider
from revold_ai_assistant.adapters.postgres.repository import PostgresProductIndexRepository
from revold_catalog.adapters.postgres.repository import PostgresProductRepository
from revold_ecommerce.application import event_handlers
from revold_messaging.webhook_factory import build_webhook_sender
from revold_notification.adapters.factory import build_notification_channel
from revold_platform.events.domain import DomainEvent
from revold_postgres.db import make_engine, make_session_factory

logger = logging.getLogger(__name__)

celery_app = Celery("event_worker", broker=settings.redis_url())

_engine = make_engine(settings.database_url())
_session_factory = make_session_factory(_engine)


@celery_app.task(name="event_worker.process_event")
def process_event(event_name: str, payload: dict[str, Any]) -> None:
    asyncio.run(_dispatch(event_name, payload))


async def _dispatch(event_name: str, payload: dict[str, Any]) -> None:
    if event_name == "product.updated":
        llm = build_llm_provider(settings.llm_settings())
        async with _session_factory() as session:
            ok = await event_handlers.handle_product_updated(
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
        await event_handlers.handle_checkout_created(
            payload,
            notification_channel=build_notification_channel(settings.notification_settings()),
        )
    elif event_name == "stock.low":
        await event_handlers.handle_stock_low(
            payload,
            notification_channel=build_notification_channel(settings.notification_settings()),
        )
    else:
        # Evento sem handler registrado ainda não é um erro — é
        # extensibilidade: um domínio pode começar a publicar um evento novo
        # antes do handler correspondente existir (ex. rollout gradual).
        logger.warning("evento %r recebido sem handler registrado, ignorado", event_name)

    # Encaminhamento para webhooks de parceiro (ADR-0016) — best-effort,
    # depois do processamento interno já ter acontecido; lista vazia
    # (nenhum parceiro configurado via WEBHOOK_URLS) é o caso comum e não
    # faz nenhuma chamada de rede.
    webhook_urls = settings.webhook_urls()
    if webhook_urls:
        results = await event_handlers.forward_to_webhooks(
            DomainEvent(name=event_name, payload=payload),
            webhook_urls=webhook_urls,
            sender=build_webhook_sender(settings.webhook_sender_provider()),
        )
        for url, delivered in results.items():
            if not delivered:
                logger.warning("webhook para %r não confirmou entrega de %r", url, event_name)
