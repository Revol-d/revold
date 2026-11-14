"""Entidades do domínio de pedidos (ADR-0023)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


@dataclass(frozen=True, slots=True)
class Money:
    """Value object próprio de core-orders — não importa core_cart.domain.Money
    nem core_catalog.domain.Money de propósito (bounded contexts não
    compartilham modelo de domínio, só contratos/eventos, ver ADR-0002)."""

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money.amount não pode ser negativo")


@dataclass(frozen=True, slots=True)
class OrderLine:
    """Linha de pedido — cópia congelada do item do carrinho no momento do
    checkout. Mesmo se o produto mudar de preço ou sumir do catálogo depois,
    o pedido continua mostrando o que foi de fato vendido."""

    sku: str
    product_name: str
    variant_label: str
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError("quantity deve ser >= 1")

    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)


class PaymentStatus(str, Enum):
    """Nesta onda (ADR-0023), a confirmação de pagamento ainda é manual —
    a Nick marca PAID pelo admin-dashboard depois de confirmar pelo
    WhatsApp. Quando core-payments (próxima onda) existir, um webhook do
    gateway passa a fazer essa transição sozinho, sem mudar este enum."""

    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class FulfillmentStatus(str, Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class InvalidOrderTransition(Exception):
    """Levantada quando uma transição de status não é permitida no estado
    atual do pedido (ex.: marcar como enviado um pedido ainda não pago)."""


class OrderNotFound(Exception):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Pedido '{order_id}' não encontrado")
        self.order_id = order_id


@dataclass(slots=True)
class Order:
    order_id: str
    cart_id: str
    lines: tuple[OrderLine, ...]
    currency: str = "BRL"
    payment_status: PaymentStatus = PaymentStatus.PENDING
    fulfillment_status: FulfillmentStatus = FulfillmentStatus.PENDING
    created_at: str = ""  # ISO 8601 — preenchido pelo caso de uso/adapter

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError("Pedido precisa de ao menos uma linha")

    def total(self) -> Money:
        total = Decimal("0")
        for line in self.lines:
            total += line.subtotal().amount
        return Money(total, self.currency)

    def mark_paid(self) -> None:
        if self.payment_status != PaymentStatus.PENDING:
            raise InvalidOrderTransition(
                f"Só é possível marcar como pago um pedido PENDING (atual: {self.payment_status.value})"
            )
        self.payment_status = PaymentStatus.PAID

    def cancel(self) -> None:
        """Cancelamento só é permitido antes da confirmação de pagamento —
        um pedido já pago exige estorno (fluxo de `core-payments`, fora do
        escopo desta onda), não só uma mudança de status aqui."""
        if self.payment_status != PaymentStatus.PENDING:
            raise InvalidOrderTransition(
                f"Só é possível cancelar um pedido PENDING (atual: {self.payment_status.value})"
            )
        self.payment_status = PaymentStatus.CANCELLED

    def mark_shipped(self) -> None:
        if self.payment_status != PaymentStatus.PAID:
            raise InvalidOrderTransition("Só é possível enviar um pedido já pago")
        if self.fulfillment_status != FulfillmentStatus.PENDING:
            raise InvalidOrderTransition(
                f"fulfillment_status atual ({self.fulfillment_status.value}) já passou de PENDING"
            )
        self.fulfillment_status = FulfillmentStatus.SHIPPED

    def mark_delivered(self) -> None:
        if self.fulfillment_status != FulfillmentStatus.SHIPPED:
            raise InvalidOrderTransition(
                "Só é possível marcar como entregue um pedido já enviado (SHIPPED)"
            )
        self.fulfillment_status = FulfillmentStatus.DELIVERED
