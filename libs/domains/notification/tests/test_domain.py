from __future__ import annotations

import pytest
from revold_testing.notification_factories import NotificationFactory

from revold_notification.domain import Notification


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


class TestFabricaDeDados:
    def test_mensagem_com_acento_e_emoji_e_preservada(self) -> None:
        # A mensagem real que a Nick recebe pode ter acento/emoji (nome de
        # produto, endereço) — uma fixture "new_checkout"/"algo" nunca
        # pegaria uma normalização/encoding acidental no canal de e-mail
        # (ADR-0018) ou no worker (ADR-0013).
        notification = NotificationFactory(message="🎉 Novo pedido: Vestido Midi Ção")
        assert notification.message == "🎉 Novo pedido: Vestido Midi Ção"

    def test_fabrica_gera_event_type_dentre_os_eventos_reais_do_sistema(self) -> None:
        notification = NotificationFactory()
        assert notification.event_type in {"new_checkout", "low_stock"}
