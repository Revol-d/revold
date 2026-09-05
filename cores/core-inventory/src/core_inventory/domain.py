"""Entidades e regras do domínio de estoque."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StockLevel:
    """Nível de estoque de um SKU.

    quantity_on_hand: quantidade fisicamente em estoque.
    quantity_reserved: quantidade já comprometida com carrinhos em
    checkout, mas ainda não baixada do estoque físico — o checkout do
    revold é manual via WhatsApp (ADR-0005), então a baixa definitiva só
    acontece quando Nick confirma o pagamento (ver `fulfill`).
    """

    sku: str
    quantity_on_hand: int = 0
    quantity_reserved: int = 0

    def __post_init__(self) -> None:
        if self.quantity_on_hand < 0:
            raise ValueError("quantity_on_hand não pode ser negativo")
        if self.quantity_reserved < 0:
            raise ValueError("quantity_reserved não pode ser negativo")
        if self.quantity_reserved > self.quantity_on_hand:
            raise ValueError("quantity_reserved não pode exceder quantity_on_hand")

    @property
    def quantity_available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved

    def reserve(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity deve ser positiva")
        if quantity > self.quantity_available:
            raise InsufficientStock(self.sku, requested=quantity, available=self.quantity_available)
        self.quantity_reserved += quantity

    def release(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity deve ser positiva")
        if quantity > self.quantity_reserved:
            raise ValueError("não é possível liberar mais do que está reservado")
        self.quantity_reserved -= quantity

    def receive(self, quantity: int) -> None:
        """Entrada de estoque (reposição/inventário inicial)."""
        if quantity <= 0:
            raise ValueError("quantity deve ser positiva")
        self.quantity_on_hand += quantity

    def fulfill(self, quantity: int) -> None:
        """Baixa definitiva do estoque físico após confirmação manual da
        venda (Nick confirma o pagamento pelo WhatsApp, ADR-0005)."""
        if quantity <= 0:
            raise ValueError("quantity deve ser positiva")
        if quantity > self.quantity_reserved:
            raise ValueError("não é possível confirmar mais do que está reservado")
        self.quantity_on_hand -= quantity
        self.quantity_reserved -= quantity


class InsufficientStock(Exception):
    """Levantada ao tentar reservar mais do que há disponível."""

    def __init__(self, sku: str, *, requested: int, available: int) -> None:
        super().__init__(
            f"Estoque insuficiente para '{sku}': solicitado {requested}, disponível {available}"
        )
        self.sku = sku
        self.requested = requested
        self.available = available


class StockLevelNotFound(Exception):
    """Levantada quando não existe registro de estoque para o SKU."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"Nível de estoque para '{sku}' não encontrado")
        self.sku = sku
