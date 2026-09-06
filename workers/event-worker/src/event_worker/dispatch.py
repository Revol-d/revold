"""Lógica de despacho de evento — pura, testada com fakes (ver
tests/test_dispatch.py), sem nenhuma dependência de infraestrutura real.

Cross-core orchestration: cada handler compõe core-catalog/core-ai-assistant
ou core-notification a partir de um evento primitivo (ADR-0002 — nenhum
core importa outro), do mesmo jeito que workers/catalog-indexer/reindex.py
e apps/api_gateway/orchestration.py já fazem. `event_worker.celery_app` é
quem chama estas funções com as dependências reais montadas (Postgres,
LLMProvider, NotificationChannel configurados).
"""
from __future__ import annotations

from typing import Any

from catalog_indexer.reindex import reindex_one_product
from core_ai_assistant.ports import LLMProvider, ProductIndex
from core_ai_assistant.use_cases import IndexProduct
from core_catalog.ports import ProductRepository
from core_events.domain import DomainEvent
from core_events.ports import WebhookSender
from core_notification.ports import NotificationChannel
from core_notification.use_cases import NotifyLowStock, NotifyNewCheckout


async def handle_product_updated(
    payload: dict[str, Any],
    *,
    product_repository: ProductRepository,
    llm: LLMProvider,
    index: ProductIndex,
) -> bool:
    """Reindexa só o SKU do evento. Retorna False se o produto já não existe
    mais (corrida esperada entre publicação e consumo assíncronos — ver
    catalog_indexer.reindex.reindex_one_product)."""
    index_product = IndexProduct(llm, index)
    return await reindex_one_product(payload["sku"], product_repository, index_product)


async def handle_checkout_created(
    payload: dict[str, Any], *, notification_channel: NotificationChannel
) -> None:
    await NotifyNewCheckout(notification_channel).execute(
        cart_id=payload["cart_id"], summary_text=payload["summary_text"]
    )


async def handle_stock_low(payload: dict[str, Any], *, notification_channel: NotificationChannel) -> None:
    await NotifyLowStock(notification_channel).execute(
        sku=payload["sku"],
        quantity_available=payload["quantity_available"],
        threshold=payload["threshold"],
    )


async def forward_to_webhooks(
    event: DomainEvent, *, webhook_urls: list[str], sender: WebhookSender
) -> dict[str, bool]:
    """Encaminha o evento para cada parceiro/integração inscrito (ADR-0016)
    — lista vazia é o caso comum (nenhum parceiro configurado ainda) e não
    faz nenhuma chamada. Um destino falhando (após os retries do próprio
    `sender`) não afeta os demais nem o processamento interno do evento —
    entrega de webhook é best-effort, o consumo interno (reindexação,
    notificação) já aconteceu antes disso."""
    return {url: await sender.send(url, event) for url in webhook_urls}
