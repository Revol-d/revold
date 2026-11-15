from __future__ import annotations

from revold_notification.adapters.logging_channel import LoggingNotificationChannel
from revold_notification.domain import Notification


async def test_send_registra_notificacao_em_memoria(caplog) -> None:
    channel = LoggingNotificationChannel()
    notification = Notification(event_type="new_checkout", message="Carrinho c1 em checkout")

    with caplog.at_level("INFO", logger="revold.notifications"):
        await channel.send(notification)

    assert channel.sent == [notification]
    assert "new_checkout" in caplog.text
    assert "Carrinho c1 em checkout" in caplog.text
