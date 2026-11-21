"""Testes de integração do PostgresProductRepository contra um Postgres de
verdade — o resto da suíte de `catalog` só testa contra o fake em
memória (libs/domains/catalog/tests/conftest.py). Isso deixava sem cobertura
justo o código mais arriscado: o SQL de verdade, e em especial a
reconciliação de variantes por SKU em `save_product` (ver o comentário
naquele método) — um bug real de conflito de primary key só apareceria
rodando contra um banco de verdade, nunca contra o dict do fake.

Pula (skip) automaticamente se TEST_DATABASE_URL/DATABASE_URL não apontar
pra um Postgres alcançável — não quebra CI nem outros ambientes sem
Postgres.

A conformidade geral (CRUD, variantes, filtro de tamanho/cor, ordenação por
preço, delete) chama a função compartilhada em
tests/support/revold_testing/port_conformance.py, que
test_catalog_repository_integration_azure_sql.py também chama. Os testes de
busca full-text ficam SEPARADOS (não compartilhados): o ranking de relevância
é definido por adapter (ver ADR-0014 e o plano de migração Postgres -> Azure
SQL, docs internos) -- Postgres e Azure SQL têm mecanismos de busca
genuinamente diferentes por baixo, não só sintaxe diferente.
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_catalog.adapters.postgres.repository import PostgresProductRepository
from revold_catalog.domain import Category, Money, Product
from revold_testing.port_conformance import (
    assert_product_repository_bulk_roundtrip,
    assert_product_repository_conformance,
)

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
    ),
)


@pytest.fixture
async def repository():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — qualquer falha de conexão vira skip
        await engine.dispose()
        pytest.skip(f"Postgres de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE catalog_product_variants, catalog_products, "
                "catalog_categories RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
        yield PostgresProductRepository(session)
    await engine.dispose()


@pytest.fixture
async def camisetas(repository: PostgresProductRepository) -> Category:
    category = Category(slug="camisetas", name="Camisetas")
    await repository.save_category(category)
    return category


async def test_conformidade_da_porta_product_repository(repository) -> None:
    """Prova mecânica de que o adapter Postgres satisfaz a mesma porta que o
    adapter Azure SQL (test_catalog_repository_integration_azure_sql.py chama a
    mesma função) -- não cobre busca, ver docstring do módulo."""
    await assert_product_repository_conformance(repository)


async def test_lote_de_produtos_realistas_e_unicode(repository) -> None:
    await assert_product_repository_bulk_roundtrip(repository)


class TestBuscaFullTextDoPostgres:
    """Específicos do Postgres (tsvector + pt_unaccent, ADR-0014) -- não
    compartilhados com o adapter Azure SQL, que usa um mecanismo diferente
    (CONTAINSTABLE + FORMSOF + TRANSLATE, ver repository.py do adapter
    azure_sql) e pode ranquear/tolerar casos diferentes."""

    async def test_busca_full_text_por_palavra_de_verdade(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        await repository.save_product(
            Product(
                sku="CAM-001",
                name="Camiseta Listrada",
                category=camisetas,
                price=Money(Decimal("50")),
                variants=[],
            )
        )
        await repository.save_product(
            Product(
                sku="CAL-001",
                name="Calça Jeans",
                category=camisetas,
                price=Money(Decimal("120")),
                variants=[],
            )
        )

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="LISTRADA"
        )
        assert total == 1
        assert items[0].sku == "CAM-001"

    async def test_busca_full_text_tolera_falta_de_acento(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        """Achado real do ADR-0014: com ILIKE, buscar "camiseta" (sem
        acento) nunca casava com um nome que tivesse variação acentuada
        (ou vice-versa). A configuração pt_unaccent normaliza os dois lados
        antes de comparar."""
        await repository.save_product(
            Product(
                sku="CAM-001",
                name="Vestido Rendado",
                description="Vestido com renda francesa, ideal pra ocasião especial",
                category=camisetas,
                price=Money(Decimal("199.90")),
                variants=[],
            )
        )

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="ocasiao"
        )
        assert total == 1
        assert items[0].sku == "CAM-001"

    async def test_busca_full_text_tolera_plural(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        await repository.save_product(
            Product(
                sku="CAM-002",
                name="Camisetas Básicas",
                category=camisetas,
                price=Money(Decimal("39.90")),
                variants=[],
            )
        )

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="camiseta"
        )
        assert total == 1
        assert items[0].sku == "CAM-002"

    async def test_busca_full_text_ordena_por_relevancia(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        """Produto com o termo buscado repetido no nome E na descrição deve
        rankear acima de um produto que só menciona o termo uma vez —
        comportamento que o ILIKE (ordenado por SKU) nunca teve."""
        await repository.save_product(
            Product(
                sku="Z-MENOS-RELEVANTE",
                name="Bolsa com detalhe listrado",
                category=camisetas,
                price=Money(Decimal("89.90")),
                variants=[],
            )
        )
        await repository.save_product(
            Product(
                sku="A-MAIS-RELEVANTE",
                name="Camiseta Listrada",
                description="Camiseta listrada, listras horizontais",
                category=camisetas,
                price=Money(Decimal("50")),
                variants=[],
            )
        )

        items, _total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="listrada", sort="relevance"
        )
        assert [p.sku for p in items] == ["A-MAIS-RELEVANTE", "Z-MENOS-RELEVANTE"]
