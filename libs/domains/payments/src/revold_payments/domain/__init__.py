"""Entidades do domínio de pagamento (ADR-0024)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


@dataclass(frozen=True, slots=True)
class Money:
    """Value object próprio de `payments` — não importa Money de
    nenhum outro core de propósito (bounded contexts não compartilham
    modelo de domínio, ver ADR-0002)."""

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Money.amount de uma cobrança precisa ser positivo")


class PaymentMethod(str, Enum):
    PIX = "pix"
    CREDIT_CARD = "credit_card"


class ChargeStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvalidChargeTransition(Exception):
    pass


class ChargeNotFound(Exception):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Cobrança '{identifier}' não encontrada")
        self.identifier = identifier


@dataclass(slots=True)
class Charge:
    """Uma cobrança contra um pedido (`order_id` — referência solta, ver
    docstring do pacote). `provider_charge_id` é o id do lado do gateway
    (Mercado Pago, etc.) — é por ele que um webhook encontra a cobrança
    correspondente aqui dentro."""

    charge_id: str
    order_id: str
    provider: str
    provider_charge_id: str
    method: PaymentMethod
    amount: Money
    status: ChargeStatus = ChargeStatus.PENDING
    # Pix: QR code (imagem) e "copia e cola" (string) para o cliente pagar.
    pix_qr_code: str | None = None
    pix_copy_paste: str | None = None
    # Cartão: URL de checkout hospedado do provedor — o cartão nunca é
    # digitado em formulário nosso, evita escopo PCI-DSS (ver ADR-0024).
    checkout_url: str | None = None
    created_at: str = ""

    def mark_paid(self) -> None:
        if self.status != ChargeStatus.PENDING:
            raise InvalidChargeTransition(
                f"Só é possível confirmar pagamento de uma cobrança PENDING (atual: {self.status.value})"
            )
        self.status = ChargeStatus.PAID

    def mark_failed(self) -> None:
        if self.status != ChargeStatus.PENDING:
            raise InvalidChargeTransition(
                f"Só é possível marcar como falha uma cobrança PENDING (atual: {self.status.value})"
            )
        self.status = ChargeStatus.FAILED

    def mark_expired(self) -> None:
        if self.status != ChargeStatus.PENDING:
            raise InvalidChargeTransition(
                f"Só é possível expirar uma cobrança PENDING (atual: {self.status.value})"
            )
        self.status = ChargeStatus.EXPIRED

    def mark_refunded(self) -> None:
        """Estorno — fora de escopo desta onda chamar isto a partir de um
        caso de uso público (ver ADR-0024, "não implementado nesta
        onda"), mas o domínio já sabe representar o estado."""
        if self.status != ChargeStatus.PAID:
            raise InvalidChargeTransition("Só é possível estornar uma cobrança já PAID")
        self.status = ChargeStatus.REFUNDED
