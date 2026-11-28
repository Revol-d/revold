"""Modelos SQLAlchemy do catálogo no Azure SQL. Vivem só no adapter -- revold_catalog
não os conhece.

Três diferenças reais em relação a adapters/postgres/models.py (não são só troca de
import):

1. `images`: era `ARRAY(String)` (só existe no Postgres) -- vira `JSON` aqui (decisão
   do plano de migração: mais simples que uma tabela filha, é um detalhe interno do
   adapter, a porta ProductRepository não muda).
2. `search_text`: substitui o `search_vector` (`TSVECTOR` + `to_tsvector('pt_unaccent',
   ...)`, só Postgres) por uma coluna computada com `TRANSLATE` tirando o acento à mão
   -- testado e confirmado na Fase 0: uma colação accent-insensitive NÃO basta pro
   full-text do SQL Server (`CONTAINS`/`FREETEXT`/`CONTAINSTABLE` ignoram a colação).
   O índice full-text em cima desta coluna é criado na migração via SQL cru (não dá
   pra expressar `CREATE FULLTEXT INDEX` como metadata do SQLAlchemy) -- ver
   adapters/azure_sql/repository.py para como a busca usa isso.
3. `name`/`description`/`search_text`/`color` usam `Unicode`/`UnicodeText`
   (`NVARCHAR`/`NTEXT`), não `String`/`Text` (`VARCHAR`/`TEXT`) -- achado de revisão
   do store-settings: `VARCHAR`/`TEXT` com a colação padrão do servidor trocam
   caractere fora do CP1252 por `?` ao gravar, sem erro. `search_text` segue o
   mesmo tipo porque `TRANSLATE` opera sobre `name`/`description`.
4. `sku`/`product_sku` usam `Unicode` com colação binária, não `String` puro -- mesmo
   achado do #23 (inventory): com a colação padrão do servidor, SKUs que só diferem
   em maiúsculas (ou fora do CP1252) dividiriam a mesma linha, sem erro.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Computed, ForeignKey, Index, Numeric, String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from revold_azure_sql.db import Base

# Mesma colação usada em inventory (#23): compara o valor exato, como o Postgres faz.
SKU_COLLATION = "Latin1_General_100_BIN2"

# Mesmo mapeamento usado em repository.py pra normalizar o termo de busca do lado do
# app -- as duas pontas (coluna indexada e termo buscado) precisam passar pela MESMA
# normalização, senão "camisetá" nunca bate com "Camiseta" (ver ADR-0014 original: é
# exatamente isso que o unaccent do Postgres faz sozinho, e aqui precisa ser explícito).
ACCENTED_CHARS = "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ"
PLAIN_CHARS = "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC"


class CategoryModel(Base):
    __tablename__ = "catalog_categories"

    slug: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(200), nullable=False)

    products: Mapped[list["ProductModel"]] = relationship(back_populates="category")


class ProductModel(Base):
    __tablename__ = "catalog_products"
    __table_args__ = (Index("ix_catalog_products_category_slug", "category_slug"),)

    sku: Mapped[str] = mapped_column(Unicode(64, collation=SKU_COLLATION), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    description: Mapped[str] = mapped_column(UnicodeText, default="")
    category_slug: Mapped[str] = mapped_column(ForeignKey("catalog_categories.slug"))
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), default="BRL")
    original_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    search_text: Mapped[str | None] = mapped_column(
        UnicodeText,
        Computed(
            "TRANSLATE(COALESCE(name, N'') + N' ' + COALESCE(description, N''), "
            f"N'{ACCENTED_CHARS}', N'{PLAIN_CHARS}')",
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

    sku: Mapped[str] = mapped_column(Unicode(64, collation=SKU_COLLATION), primary_key=True)
    product_sku: Mapped[str] = mapped_column(
        Unicode(64, collation=SKU_COLLATION), ForeignKey("catalog_products.sku")
    )
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    color: Mapped[str] = mapped_column(Unicode(60), nullable=False)
    in_stock: Mapped[bool] = mapped_column(default=True)

    product: Mapped[ProductModel] = relationship(back_populates="variants")
