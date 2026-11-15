"""Orquestração de estoque que cruza domínios, usada pelas rotas do api-gateway.

Vive no produto — e não em nenhum domínio — porque cruza bounded contexts:
`inventory` não conhece `revold_platform.events` nem `orders` (ADR-0002),
então quem decide "isso é pouco estoque, publica o evento" e "pedido pago,
dá baixa no reservado" é o produto, não revold_inventory (ADR-0027).
"""
from __future__ import annotations

import logging

from revold_platform.events.domain import DomainEvent
from revold_platform.events.ports import EventPublisher
from revold_inventory.domain import StockLevel, StockLevelNotFound
from revold_inventory.ports import InventoryRepository
from revold_inventory.application.use_cases import FulfillReservedStock
from revold_platform.observability.ports import MetricsPublisher
from revold_orders.domain import Order

logger = logging.getLogger("revold.orders")


async def notify_if_low_stock(
    stock: StockLevel,
    event_publisher: EventPublisher,
    threshold: int,
    metrics: MetricsPublisher | None = None,
) -> None:
    """Publica `stock.low` quando a quantidade disponível cai abaixo do
    limiar — quem realmente notifica a Nick (ver
    revold_ecommerce.application.event_handlers.handle_stock_low, ADR-0013) roda de
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


async def fulfill_order_stock(order: Order, inventory_repository: InventoryRepository) -> None:
    """Baixa definitiva do estoque reservado de cada linha do pedido —
    chamado quando o pagamento é confirmado, manualmente em `/pedidos`
    (api_gateway.routers.orders.update_payment_status) ou automaticamente
    pelo webhook do gateway (api_gateway.routers.payments, ADR-0024).

    `inventory` não conhece `orders` (ADR-0002); `FulfillReservedStock`
    (`inventory`) já existia desde antes de `payments`, mas não tinha
    nenhum chamador — ADR-0023 deixou isso registrado como limitação
    deliberada até este momento. Uma inconsistência de estoque (SKU sem
    registro, ou reservado insuficiente — ex.: catálogo mudou depois do
    pedido) fica só logada: o pagamento já foi confirmado e não deve ser
    revertido por causa disso, a Nick reconcilia manualmente se aparecer no
    log."""
    for line in order.lines:
        try:
            await FulfillReservedStock(inventory_repository).execute(line.sku, line.quantity)
        except (StockLevelNotFound, ValueError) as exc:
            logger.warning(
                "Não foi possível confirmar baixa de estoque do pedido %s (sku=%s, quantity=%s): %s",
                order.order_id,
                line.sku,
                line.quantity,
                exc,
            )
