"""Funções de orquestração compartilhadas entre routers do api-gateway.

Vivem aqui — e não em nenhum core — porque cruzam bounded contexts:
core-inventory não conhece core-events (ADR-0002), então quem decide
"isso é pouco estoque, publica o evento" é o api-gateway, não
core_inventory.
"""
from __future__ import annotations

from core_events.domain import DomainEvent
from core_events.ports import EventPublisher
from core_inventory.domain import StockLevel
from core_observability.ports import MetricsPublisher


async def notify_if_low_stock(
    stock: StockLevel,
    event_publisher: EventPublisher,
    threshold: int,
    metrics: MetricsPublisher | None = None,
) -> None:
    """Publica `stock.low` quando a quantidade disponível cai abaixo do
    limiar — quem realmente notifica a Nick (ver
    workers/event_worker.dispatch.handle_stock_low, ADR-0013) roda de
    forma assíncrona, fora do caminho da requisição HTTP: se o canal de
    notificação falhar ou demorar, isso não deve travar nem falhar a
    reserva de estoque em si.

    `metrics` é opcional (ADR-0017) de propósito — nenhum teste existente
    de cart/inventory precisa passar um fake de MetricsPublisher só para
    continuar funcionando; quando ausente, simplesmente não incrementa
    nada."""
    if stock.quantity_available < threshold:
        await event_publisher.publish(
            DomainEvent(
                name="stock.low",
                payload={
                    "sku": stock.sku,
                    "quantity_available": stock.quantity_available,
                    "threshold": threshold,
                },
            )
        )
        if metrics is not None:
            metrics.increment("stock_low_total")
