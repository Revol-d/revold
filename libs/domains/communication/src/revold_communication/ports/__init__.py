"""Porta de handoff de checkout (ADR-0005).

A primeira implementação (whatsapp_clicktochat) não automatiza nada — só
monta um link de conversa. Uma segunda implementação futura (WhatsApp
Business API oficial) pode automatizar confirmação/notificação sem mudar
quem chama esta porta.
"""
from __future__ import annotations

from typing import Protocol

from revold_communication.domain import CartSummary


class CheckoutHandoff(Protocol):
    provider_name: str

    def build_handoff(self, summary: CartSummary) -> str:
        """Retorna a URL/ação que leva o cliente a concluir a compra com a Nick."""
        ...
