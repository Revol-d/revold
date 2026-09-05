"""Porta (interface) que core-notification espera que a infraestrutura implemente.

Qualquer adapter (WhatsApp Business API futura, e-mail, um logger de
desenvolvimento) implementa este Protocol. core-notification nunca importa
um cliente HTTP nem SDK de mensageria.
"""
from __future__ import annotations

from typing import Protocol

from core_notification.domain import Notification


class NotificationChannel(Protocol):
    async def send(self, notification: Notification) -> None: ...
