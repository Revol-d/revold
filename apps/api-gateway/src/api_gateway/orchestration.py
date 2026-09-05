"""Funções de orquestração compartilhadas entre routers do api-gateway.

Vivem aqui — e não em nenhum core — porque cruzam bounded contexts:
core-inventory não conhece core-notification (ADR-0002), então quem decide
"isso é pouco estoque, avisa a Nick" é o api-gateway, não core_inventory.
"""
from __future__ import annotations

from core_inventory.domain import StockLevel
from core_notification.ports import NotificationChannel
from core_notification.use_cases import NotifyLowStock


async def notify_if_low_stock(
    stock: StockLevel, notification_channel: NotificationChannel, threshold: int
) -> None:
    if stock.quantity_available < threshold:
        await NotifyLowStock(notification_channel).execute(
            sku=stock.sku, quantity_available=stock.quantity_available, threshold=threshold
        )
