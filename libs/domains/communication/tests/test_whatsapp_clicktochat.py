from __future__ import annotations

import pytest

from revold_communication.adapters.whatsapp_clicktochat import WhatsAppClickToChatCheckout
from revold_communication.domain import CartSummary, CartSummaryLine


def test_build_handoff_gera_link_wa_me_com_resumo():
    checkout = WhatsAppClickToChatCheckout(whatsapp_number="5511999999999")
    summary = CartSummary(
        lines=(
            CartSummaryLine(
                product_name="Camiseta Básica",
                variant_label="M / Branco",
                quantity=2,
                unit_price_amount="79.90",
            ),
        ),
        total_amount="159.80",
    )

    url = checkout.build_handoff(summary)

    assert url.startswith("https://wa.me/5511999999999?text=")
    assert "Camiseta" in url or "Camiseta" in url  # url-encoded, checado abaixo
    from urllib.parse import unquote

    assert "Camiseta Básica" in unquote(url)
    assert "159.80" in unquote(url)


def test_build_handoff_sem_numero_configurado_levanta_erro():
    checkout = WhatsAppClickToChatCheckout(whatsapp_number="")
    with pytest.raises(ValueError):
        checkout.build_handoff(CartSummary(lines=(), total_amount="0.00"))
