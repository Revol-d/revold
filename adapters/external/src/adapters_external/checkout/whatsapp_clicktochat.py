"""Implementação da porta CheckoutHandoff via link de clique-para-conversar do
WhatsApp (ADR-0005) — sem WhatsApp Business API, sem aprovação da Meta.
"""
from __future__ import annotations

import os
from urllib.parse import quote

from core_communication.domain import CartSummary


class WhatsAppClickToChatCheckout:
    provider_name = "whatsapp-clicktochat"

    def __init__(self, whatsapp_number: str | None = None) -> None:
        self._number = whatsapp_number or os.environ.get("NICK_WHATSAPP_NUMBER", "")

    def build_handoff(self, summary: CartSummary) -> str:
        if not self._number:
            raise ValueError(
                "NICK_WHATSAPP_NUMBER não configurado — ver .env.example (ADR-0005)."
            )
        message_lines = ["Olá! Quero fechar esta compra:"]
        for line in summary.lines:
            message_lines.append(
                f"- {line.quantity}x {line.product_name} ({line.variant_label}) "
                f"— {line.unit_price_amount} {summary.currency}"
            )
        message_lines.append(f"Total: {summary.total_amount} {summary.currency}")
        message = "\n".join(message_lines)
        return f"https://wa.me/{self._number}?text={quote(message)}"
