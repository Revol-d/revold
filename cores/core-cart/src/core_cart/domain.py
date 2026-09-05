from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """Value object próprio de core-cart — não importa core_catalog.domain.Money
    de propósito (bounded contexts não compartilham modelo de domínio,
    só contratos/eventos, ver ADR-0002)."""

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money.amount não pode ser negativo")

    def __add__(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise ValueError("Não é possível somar valores em moedas diferentes")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: int) -> "Money":
        return Money(self.amount * factor, self.currency)


@dataclass(slots=True)
class CartItem:
    sku: str
    name: str
    variant_label: str  # ex.: "M / Azul"
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError("quantity deve ser >= 1")

    def subtotal(self) -> Money:
        return self.unit_price * self.quantity


class CartItemNotFound(Exception):
    def __init__(self, sku: str) -> None:
        super().__init__(f"Item '{sku}' não está no carrinho")
        self.sku = sku


class EmptyCart(Exception):
    pass


@dataclass(slots=True)
class Cart:
    cart_id: str
    items: list[CartItem] = field(default_factory=list)
    currency: str = "BRL"

    def total(self) -> Money:
        total = Money(Decimal("0"), self.currency)
        for item in self.items:
            total = total + item.subtotal()
        return total

    def find_item(self, sku: str) -> CartItem | None:
        return next((i for i in self.items if i.sku == sku), None)

    def add_item(
        self, *, sku: str, name: str, variant_label: str, unit_price: Money, quantity: int = 1
    ) -> None:
        existing = self.find_item(sku)
        if existing is not None:
            existing.quantity += quantity
            return
        self.items.append(
            CartItem(
                sku=sku,
                name=name,
                variant_label=variant_label,
                unit_price=unit_price,
                quantity=quantity,
            )
        )

    def update_item_quantity(self, sku: str, quantity: int) -> None:
        item = self.find_item(sku)
        if item is None:
            raise CartItemNotFound(sku)
        if quantity < 1:
            raise ValueError("quantity deve ser >= 1")
        item.quantity = quantity

    def remove_item(self, sku: str) -> None:
        item = self.find_item(sku)
        if item is None:
            raise CartItemNotFound(sku)
        self.items.remove(item)
