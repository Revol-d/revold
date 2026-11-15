"""Value objects usados na comunicação com canais externos.

CartSummary é passado por valor pelo orchestrator que compõe `cart` com
`communication` — `communication` nunca importa revold_cart diretamente
(ver ADR-0002: cores não se importam entre si)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CartSummaryLine:
    product_name: str
    variant_label: str  # ex.: "M / Azul"
    quantity: int
    unit_price_amount: str  # string decimal, mesmo motivo de revold_catalog.domain.Money


@dataclass(frozen=True, slots=True)
class CartSummary:
    lines: tuple[CartSummaryLine, ...]
    total_amount: str
    currency: str = "BRL"
