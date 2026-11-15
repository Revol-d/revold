"""Entidades e value objects do domínio de catálogo."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """Value object de dinheiro. Nunca usar float para preço."""

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money.amount não pode ser negativo")
        if len(self.currency) != 3:
            raise ValueError("Money.currency deve ser um código ISO 4217 de 3 letras")


@dataclass(frozen=True, slots=True)
class Category:
    slug: str
    name: str


@dataclass(frozen=True, slots=True)
class ProductVariant:
    sku: str
    size: str
    color: str
    in_stock: bool


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    category: Category
    price: Money
    variants: list[ProductVariant]
    images: list[str] = field(default_factory=list)
    description: str = ""
    original_price: Money | None = None

    def is_available(self) -> bool:
        return any(variant.in_stock for variant in self.variants)


class ProductNotFound(Exception):
    """Levantada quando um SKU de produto não existe no catálogo."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"Produto '{sku}' não encontrado")
        self.sku = sku


class CategoryNotFound(Exception):
    """Levantada ao tentar criar um produto numa categoria que não existe."""

    def __init__(self, slug: str) -> None:
        super().__init__(f"Categoria '{slug}' não encontrada")
        self.slug = slug


class DuplicateSku(Exception):
    """Levantada ao tentar criar um produto com um SKU que já existe."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"Produto com SKU '{sku}' já existe")
        self.sku = sku


class DuplicateVariantSku(Exception):
    """Levantada ao tentar adicionar, a um produto, uma variante cujo SKU já
    existe nesse mesmo produto."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"Já existe uma variante com SKU '{sku}' neste produto")
        self.sku = sku


class VariantNotFound(Exception):
    """Levantada ao tentar editar/remover uma variante que não existe no
    produto informado."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"Variante '{sku}' não encontrada neste produto")
        self.sku = sku


class CategoryHasProducts(Exception):
    """Levantada ao tentar remover uma categoria que ainda tem produtos —
    nunca cascade-remove produtos junto (perda de dado silenciosa); quem
    remove precisa primeiro mover ou remover os produtos da categoria."""

    def __init__(self, slug: str, product_count: int) -> None:
        super().__init__(
            f"Categoria '{slug}' ainda tem {product_count} produto(s) — mova ou remova-os antes"
        )
        self.slug = slug
        self.product_count = product_count
