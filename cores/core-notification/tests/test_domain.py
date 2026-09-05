from __future__ import annotations

import pytest

from core_notification.domain import Notification


def test_notification_holds_event_type_and_message() -> None:
    notification = Notification(event_type="new_checkout", message="Carrinho c1 em checkout")
    assert notification.event_type == "new_checkout"
    assert notification.message == "Carrinho c1 em checkout"


def test_notification_rejects_empty_event_type() -> None:
    with pytest.raises(ValueError):
        Notification(event_type="", message="algo")


def test_notification_rejects_empty_message() -> None:
    with pytest.raises(ValueError):
        Notification(event_type="new_checkout", message="")
