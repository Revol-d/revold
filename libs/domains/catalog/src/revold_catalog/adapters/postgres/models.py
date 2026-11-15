"""Modelos SQLAlchemy do catálogo. Vivem só no adapter — revold_catalog não os conhece."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ARRAY, Computed, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revold_postgres.db import Base


class CategoryModel(Base):
    __tablename__ = "catalog_categories"

    slug: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    products: Mapped[list["ProductModel"]] = relationship(back_populates="category")


class ProductModel(Base):
    __tablename__ = "catalog_products"
    # Indices que existem no banco desde as migracoes 0001 (categoria) e 0004 (busca full-text,
    # GIN). Declarados aqui, a planta fica igual a casa
    # (products/ecommerce/tests/test_migrations_match_models.py confere).
    __table_args__ = (
        Index("ix_catalog_products_category_slug", "category_slug"),
        Index("ix_catalog_products_search_vector", "search_vector", postgresql_using="gin"),
    )

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    category_slug: Mapped[str] = mapped_column(ForeignKey("catalog_categories.slug"))
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), default="BRL")
    original_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    images: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    # Coluna gerada pelo Postgres (migration 0004, ADR-0014) — nunca
    # escrita pela aplicação; o Computed() aqui só avisa o SQLAlchemy pra
    # excluir esta coluna de INSERT/UPDATE (quem recalcula é o banco).
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('pt_unaccent', coalesce(name, '') || ' ' || coalesce(description, ''))",
            persisted=True,
        ),
        nullable=True,
    )

    category: Mapped[CategoryModel] = relationship(back_populates="products")
    variants: Mapped[list["ProductVariantModel"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariantModel(Base):
    __tablename__ = "catalog_product_variants"
    __table_args__ = (Index("ix_catalog_variants_product_sku", "product_sku"),)

    sku: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_sku: Mapped[str] = mapped_column(ForeignKey("catalog_products.sku"))
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    color: Mapped[str] = mapped_column(String(60), nullable=False)
    in_stock: Mapped[bool] = mapped_column(default=True)

    product: Mapped[ProductModel] = relationship(back_populates="variants")
