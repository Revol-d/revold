"""O link de clique-para-conversar: função pura, sem rede."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from revold_whatsapp.click_to_chat import build_click_to_chat_url


def test_url_points_to_the_number() -> None:
    url = build_click_to_chat_url("5511999999999", "oi")

    assert url.startswith("https://wa.me/5511999999999?text=")


def test_message_is_url_encoded_and_survives_the_round_trip() -> None:
    message = "Olá! Quero fechar esta compra:\n- 2x Camiseta (M / Azul) — 59.90 BRL"

    url = build_click_to_chat_url("5511999999999", message)

    assert " " not in url and "\n" not in url
    assert parse_qs(urlparse(url).query)["text"] == [message]
