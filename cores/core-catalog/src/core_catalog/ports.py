"""Portas (interfaces) que core-catalog espera que a infraestrutura implemente.

Qualquer adapter (Postgres, um fake em memória para teste, etc.) implementa
este Protocol. core-catalog nunca importa SQLAlchemy nem nenhum driver de banco.
"""
from __future__ import annotations

from typing import Protocol

from core_catalog.domain import Category, Product


class ProductRepository(Protocol):
    async def list_categories(self) -> list[Category]: ...

    async def get_category(self, slug: str) -> Category | None: ...

    async def save_category(self, category: Category) -> None:
        """Cria ou atualiza uma categoria (upsert por slug)."""
        ...

    async def list_products(
        self, *, category_slug: str | None, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        """Retorna (itens da página, total de itens que casam com o filtro)."""
        ...

    async def get_product(self, sku: str) -> Product | None: ...

    async def save_product(self, product: Product) -> None:
        """Cria ou atualiza um produto, substituindo suas variantes por completo
        (upsert por SKU)."""
        ...

    async def find_variant_owner(self, variant_sku: str) -> str | None:
        """Retorna o SKU do produto dono da variante com esse SKU, se existir
        em qualquer produto do catálogo — SKU de variante é único
        globalmente (é a mesma chave usada por core-inventory), não só
        dentro de um produto."""
        ...
