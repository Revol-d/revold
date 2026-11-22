"""Testes de integração do AzureSqlProductRepository contra um Azure SQL/SQL
Server real -- mesma convenção do teste Postgres irmão
(test_catalog_repository_integration.py): pula sozinho se
TEST_DATABASE_URL_AZURE_SQL/DATABASE_URL_AZURE_SQL não apontar pra um banco
alcançável.

A conformidade geral chama a MESMA função que o teste Postgres chama. Os testes
de busca full-text são separados (mecanismo genuinamente diferente -- ver
repository.py do adapter) e esperam **resultados equivalentes, não ranking
idêntico** ao Postgres -- ver a nota na porta ProductRepository e o plano de
migração, docs internos.

O índice full-text do SQL Server popula de forma ASSÍNCRONA (mesmo depois do
INSERT retornar) -- os testes de busca esperam o
`FULLTEXTCATALOGPROPERTY('catalog_fts', 'PopulateStatus')` voltar a 0 antes de
consultar, senão o resultado pode vir vazio por uma corrida, não por um bug
real (achado confirmado na Fase 0/nesta fase).
"""
from __future__ import annotations

import os
import time
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_catalog.adapters.azure_sql.repository import AzureSqlProductRepository
from revold_catalog.domain import Category, Money, Product, ProductVariant
from revold_testing.port_conformance import (
    assert_product_repository_bulk_roundtrip,
    assert_product_repository_conformance,
)

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL_AZURE_SQL",
    os.environ.get(
        "DATABASE_URL_AZURE_SQL",
        "mssql+aioodbc://sa:revold_dev_only_1@localhost:1433/revold"
        "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
    ),
)


async def _wait_fulltext_populated(session, timeout_seconds: int = 30) -> None:
    for _ in range(timeout_seconds):
        status = (
            await session.execute(
                text("SELECT FULLTEXTCATALOGPROPERTY('catalog_fts', 'PopulateStatus')")
            )
        ).scalar_one()
        if status == 0:
            return
        time.sleep(1)
    raise TimeoutError("full-text catalog não populou a tempo (catalog_fts)")


@pytest.fixture
async def repository():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — qualquer falha de conexão vira skip
        await engine.dispose()
        pytest.skip(f"Azure SQL de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # FK catalog_product_variants -> catalog_products -> catalog_categories:
        # apagar na ordem certa (SQL Server recusa TRUNCATE com FK, ver orders).
        await session.execute(text("DELETE FROM catalog_product_variants"))
        await session.execute(text("DELETE FROM catalog_products"))
        await session.execute(text("DELETE FROM catalog_categories"))
        await session.commit()
        yield AzureSqlProductRepository(session)
    await engine.dispose()


@pytest.fixture
async def camisetas(repository: AzureSqlProductRepository) -> Category:
    category = Category(slug="camisetas", name="Camisetas")
    await repository.save_category(category)
    return category


async def test_conformidade_da_porta_product_repository(repository) -> None:
    await assert_product_repository_conformance(repository)


async def test_lote_de_produtos_realistas_e_unicode(repository) -> None:
    await assert_product_repository_bulk_roundtrip(repository)


async def test_texto_fora_do_cp1252_sobrevive_numa_sessao_nova(
    repository: AzureSqlProductRepository, camisetas: Category
) -> None:
    # Mesmo achado de revisão do store-settings: VARCHAR/TEXT com a colação
    # padrão do servidor trocam caractere fora do CP1252 por `?` ao gravar, sem
    # erro, e a mesma sessão (expire_on_commit=False) mascara isso -- por isso
    # relê numa sessão/engine nova, não pela mesma fixture `repository`.
    produto = Product(
        sku="CAM-EMOJI",
        name="Camiseta 🛍️",
        description="Descrição com emoji 🎉 e acento: coração",
        category=camisetas,
        price=Money(Decimal("50")),
        variants=[ProductVariant(sku="CAM-EMOJI-P", size="P", color="Rosé 🌸", in_stock=True)],
    )
    await repository.save_product(produto)

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as fresh_session:
        reloaded = await AzureSqlProductRepository(fresh_session).get_product("CAM-EMOJI")
    await engine.dispose()

    assert reloaded is not None
    assert reloaded.name == "Camiseta 🛍️"
    assert reloaded.description == "Descrição com emoji 🎉 e acento: coração"
    assert reloaded.variants[0].color == "Rosé 🌸"


@pytest.mark.parametrize(
    ("primeiro_sku", "segundo_sku"),
    [("cam-001", "CAM-001"), ("SKU-日本", "SKU-中国")],
)
async def test_skus_de_produto_diferentes_nao_compartilham_a_mesma_linha(
    repository: AzureSqlProductRepository,
    camisetas: Category,
    primeiro_sku: str,
    segundo_sku: str,
) -> None:
    # Mesmo achado do #23 (inventory): com a colação padrão do servidor, SKUs que só
    # diferem em maiúsculas (ou fora do CP1252) dividiriam a mesma linha da chave
    # primária, sem erro. Relê numa sessão/engine nova, como o teste de emoji acima.
    await repository.save_product(
        Product(
            sku=primeiro_sku,
            name="Produto um",
            category=camisetas,
            price=Money(Decimal("10")),
            variants=[],
        )
    )
    await repository.save_product(
        Product(
            sku=segundo_sku,
            name="Produto dois",
            category=camisetas,
            price=Money(Decimal("20")),
            variants=[],
        )
    )

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as fresh_session:
        fresh_repository = AzureSqlProductRepository(fresh_session)
        primeiro = await fresh_repository.get_product(primeiro_sku)
        segundo = await fresh_repository.get_product(segundo_sku)
    await engine.dispose()

    assert primeiro is not None
    assert segundo is not None
    assert (primeiro.sku, primeiro.name) == (primeiro_sku, "Produto um")
    assert (segundo.sku, segundo.name) == (segundo_sku, "Produto dois")


class TestBuscaFullTextDoAzureSql:
    """Específicos do Azure SQL (CONTAINSTABLE + FORMSOF + TRANSLATE) -- ver a
    nota longa em adapters/azure_sql/repository.py. Confirma resultado
    equivalente ao Postgres, não ranking idêntico (decisão já tomada)."""

    async def test_busca_full_text_por_palavra_de_verdade(
        self, repository: AzureSqlProductRepository, camisetas: Category
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
        await _wait_fulltext_populated(repository._session)

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="LISTRADA"
        )
        assert total == 1
        assert items[0].sku == "CAM-001"

    async def test_busca_full_text_tolera_falta_de_acento(
        self, repository: AzureSqlProductRepository, camisetas: Category
    ) -> None:
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
        await _wait_fulltext_populated(repository._session)

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="ocasiao"
        )
        assert total == 1
        assert items[0].sku == "CAM-001"

    async def test_busca_full_text_tolera_plural(
        self, repository: AzureSqlProductRepository, camisetas: Category
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
        await _wait_fulltext_populated(repository._session)

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="camiseta"
        )
        assert total == 1
        assert items[0].sku == "CAM-002"

    async def test_busca_full_text_ordena_por_relevancia(
        self, repository: AzureSqlProductRepository, camisetas: Category
    ) -> None:
        """Mesmo cenário do teste Postgres (termo repetido no nome E na
        descrição deve rankear acima de uma menção única), mas via RANK do
        CONTAINSTABLE em vez de ts_rank -- mecanismo diferente, mesma
        garantia de comportamento. Os dois produtos usam a mesma forma
        gramatical da palavra ("listrada", feminino) de propósito: achado
        real do spike desta fase é que o FORMSOF(INFLECTIONAL, ...) do SQL
        Server não necessariamente conflaciona gênero ("listrado" x
        "listrada") como o stemmer em português do Postgres conflaciona --
        então este teste prova ranking por frequência, não concordância de
        gênero (isso fica para a Fase 3)."""
        await repository.save_product(
            Product(
                sku="Z-MENOS-RELEVANTE",
                name="Bolsa com estampa listrada",
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
        await _wait_fulltext_populated(repository._session)

        items, _total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="listrada", sort="relevance"
        )
        assert [p.sku for p in items] == ["A-MAIS-RELEVANTE", "Z-MENOS-RELEVANTE"]

    async def test_busca_com_varias_palavras_acha_produto_com_palavra_no_meio(
        self, repository: AzureSqlProductRepository, camisetas: Category
    ) -> None:
        # Achado de revisão: FORMSOF(INFLECTIONAL, "vestido azul") como frase única
        # exige as palavras adjacentes nessa ordem -- "Vestido Longo Azul" não batia,
        # porque "Longo" separa as duas. Corrigido para uma cláusula AND por palavra.
        await repository.save_product(
            Product(
                sku="VES-001",
                name="Vestido Longo Azul",
                category=camisetas,
                price=Money(Decimal("249.90")),
                variants=[],
            )
        )
        await _wait_fulltext_populated(repository._session)

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query="vestido azul"
        )
        assert total == 1
        assert items[0].sku == "VES-001"

    @pytest.mark.parametrize("termo", ["*", "vestido*"])
    async def test_busca_com_asterisco_nao_quebra(
        self, repository: AzureSqlProductRepository, camisetas: Category, termo: str
    ) -> None:
        # Achado de revisão: "*" sobrevivia à sanitização e ia pro FORMSOF como
        # literal, que não aceita wildcard -- o full-text recusava a sintaxe e a
        # chamada virava erro 500 em vez de uma resposta normal.
        await repository.save_product(
            Product(
                sku="VES-002",
                name="Vestido Longo Azul",
                category=camisetas,
                price=Money(Decimal("249.90")),
                variants=[],
            )
        )
        await _wait_fulltext_populated(repository._session)

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, search_query=termo
        )
        assert total == len(items)
