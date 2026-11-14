"""Porta (interface) que core-orders espera que a infraestrutura implemente.

Qualquer adapter (Postgres, um fake em memória para teste) implementa este
Protocol — core-orders nunca importa SQLAlchemy nem nenhum driver de banco.
"""
from __future__ import annotations

from typing import Protocol

from core_orders.domain import Order, PaymentStatus


class OrderRepository(Protocol):
    async def get(self, order_id: str) -> Order | None: ...

    async def save(self, order: Order) -> None:
        """Cria ou atualiza um pedido por completo (upsert por order_id)."""
        ...

    async def list(
        self,
        *,
        payment_status: PaymentStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Order], int]:
        """Retorna (itens da página, total de itens que casam com o filtro),
        mais recentes primeiro. payment_status=None não filtra."""
        ...
