"""Lógica de despacho de evento — pura, testada com fakes (ver
products/ecommerce/tests/test_event_handlers.py), sem nenhuma dependência
de infraestrutura real.

Orquestração entre domínios: cada handler compõe `catalog`/`ai-assistant`
ou `notification` a partir de um evento primitivo (ADR-0002 — nenhum
domínio importa outro), do mesmo jeito que os módulos `catalog_indexing` e
`stock` deste pacote. `event_worker.celery_app` é quem chama estas funções
com as dependências reais montadas (Postgres, LLMProvider,
NotificationChannel configurados).
"""
from __future__ import annotations

from typing import Any

from revold_ecommerce.application.catalog_indexing import reindex_one_product
from revold_ai_assistant.ports import LLMProvider, ProductIndex
from revold_ai_assistant.application.use_cases import IndexProduct
from revold_catalog.ports import ProductRepository
from revold_platform.events.domain import DomainEvent
from revold_platform.events.ports import WebhookSender
from revold_notification.ports import NotificationChannel
from revold_notification.application.use_cases import NotifyLowStock, NotifyNewCheckout


async def handle_product_updated(
    payload: dict[str, Any],
    *,
    product_repository: ProductRepository,
    llm: LLMProvider,
    index: ProductIndex,
) -> bool:
    """Reindexa só o SKU do evento. Retorna False se o produto já não existe
    mais (corrida esperada entre publicação e consumo assíncronos — ver
    revold_ecommerce.application.catalog_indexing.reindex_one_product)."""
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
