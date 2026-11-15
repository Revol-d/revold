from __future__ import annotations

import pytest

from revold_notification.domain import Notification


class FakeNotificationChannel:
    """Adapter fake em memória, mesma forma da porta NotificationChannel, só para teste."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        self.sent.append(notification)


@pytest.fixture
def fake_channel() -> FakeNotificationChannel:
    return FakeNotificationChannel()
