"""Implementação da porta CheckoutHandoff via link de clique-para-conversar do
WhatsApp (ADR-0005) — sem WhatsApp Business API, sem aprovação da Meta.

Este adapter escreve a mensagem a partir do resumo do carrinho. Quem monta o
link é `revold_whatsapp.click_to_chat` (libs/integrations/whatsapp).
"""
from __future__ import annotations

from revold_communication.domain import CartSummary
from revold_whatsapp.click_to_chat import build_click_to_chat_url


class WhatsAppClickToChatCheckout:
    provider_name = "whatsapp-clicktochat"

    def __init__(self, whatsapp_number: str = "") -> None:
        """Recebe o número de destino. Quem lê `NICK_WHATSAPP_NUMBER` é o `settings.py` do app."""
        self._number = whatsapp_number

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
        return build_click_to_chat_url(self._number, message)
