"""Portas (interfaces) que core-catalog espera que a infraestrutura implemente.

Qualquer adapter (Postgres, um fake em memória para teste, etc.) implementa
este Protocol. core-catalog nunca importa SQLAlchemy nem nenhum driver de banco.
"""
from __future__ import annotations

from typing import Protocol

from core_catalog.domain import Category, Product


class ProductRepository(Protocol):
    async def list_categories(self) -> list[Category]: ...

    async def list_products(
        self, *, category_slug: str | None, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        """Retorna (itens da página, total de itens que casam com o filtro)."""
        ...

    async def get_product(self, sku: str) -> Product | None: ...
