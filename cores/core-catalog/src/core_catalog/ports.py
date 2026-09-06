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
        self,
        *,
        category_slug: str | None,
        page: int,
        page_size: int,
        search_query: str | None = None,
        sort: str = "relevance",
        sizes: list[str] | None = None,
        colors: list[str] | None = None,
    ) -> tuple[list[Product], int]:
        """Retorna (itens da página, total de itens que casam com o filtro).

        search_query filtra por substring no nome (case-insensitive). sort é
        um de core_catalog.use_cases.VALID_SORTS — "relevance" preserva a
        ordem natural do repositório. sizes/colors filtram produtos que
        tenham ao menos uma variante casando — quando os dois são passados
        juntos, exige a MESMA variante casar tamanho E cor (não duas
        variantes diferentes do mesmo produto)."""
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

    async def delete_product(self, sku: str) -> None:
        """Remove um produto e suas variantes. Não faz nada se o SKU não
        existir (idempotente) — quem precisa de 404 checa antes com
        get_product, como as outras operações administrativas fazem."""
        ...

    async def delete_category(self, slug: str) -> None:
        """Remove uma categoria. Não faz nada se o slug não existir. Não
        verifica se há produtos ligados a ela — essa checagem é do caso de
        uso (core_catalog.use_cases.DeleteCategory), não do repositório."""
        ...
