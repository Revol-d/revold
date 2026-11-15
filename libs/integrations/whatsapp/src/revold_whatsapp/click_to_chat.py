"""Link de clique-para-conversar do WhatsApp (`wa.me`), sem WhatsApp Business API nem aprovação
da Meta (ADR-0005). Função pura: não faz chamada de rede."""

from __future__ import annotations

from urllib.parse import quote


def build_click_to_chat_url(number: str, message: str) -> str:
    """Devolve o link que abre uma conversa com `number`, com `message` já digitada."""
    return f"https://wa.me/{number}?text={quote(message)}"
