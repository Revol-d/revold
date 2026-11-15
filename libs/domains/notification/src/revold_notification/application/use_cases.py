"""Casos de uso do `notification`.

Cada caso de uso recebe só texto/primitivos (nunca tipos de outro core —
ADR-0002) e monta a Notification apropriada antes de mandar pro canal.
"""
from __future__ import annotations

from revold_notification.domain import Notification
from revold_notification.ports import NotificationChannel


class NotifyNewCheckout:
    """Dispara quando um carrinho entra em checkout (ver ADR-0005: o
    handoff é manual via WhatsApp, então este aviso é o que faz a Nick
    saber que precisa checar o WhatsApp para fechar a venda)."""

    def __init__(self, channel: NotificationChannel) -> None:
        self._channel = channel

    async def execute(self, *, cart_id: str, summary_text: str) -> None:
        await self._channel.send(
            Notification(
                event_type="new_checkout",
                message=f"Novo carrinho em checkout ({cart_id}): {summary_text}",
            )
        )


class NotifyLowStock:
    """Dispara quando a quantidade disponível de um SKU cai abaixo do
    limiar configurado, após uma reserva de estoque."""

    def __init__(self, channel: NotificationChannel) -> None:
        self._channel = channel

    async def execute(self, *, sku: str, quantity_available: int, threshold: int) -> None:
        await self._channel.send(
            Notification(
                event_type="low_stock",
                message=(
                    f"Estoque baixo para '{sku}': {quantity_available} disponível(is), "
                    f"abaixo do limiar de {threshold}."
                ),
            )
        )
