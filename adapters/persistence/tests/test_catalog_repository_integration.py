"""Testes de integração do PostgresProductRepository contra um Postgres de
verdade — o resto da suíte de core-catalog só testa contra o fake em
memória (cores/core-catalog/tests/conftest.py). Isso deixava sem cobertura
justo o código mais arriscado: o SQL de verdade, e em especial a
reconciliação de variantes por SKU em `save_product` (ver o comentário
naquele método) — um bug real de conflito de primary key só apareceria
rodando contra um banco de verdade, nunca contra o dict do fake.

Pula (skip) automaticamente se TEST_DATABASE_URL/DATABASE_URL não apontar
pra um Postgres alcançável — não quebra CI nem outros ambientes sem
Postgres. Pra rodar localmente (validado nesta sessão, sem Docker Hub):

    apt-get install -y postgresql postgresql-16-pgvector
    service postgresql start
    su postgres -c "psql -c \"CREATE USER revold WITH PASSWORD 'revold_dev_only' SUPERUSER;\""
    su postgres -c "psql -c 'CREATE DATABASE revold OWNER revold;'"
    su postgres -c "psql -d revold -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
    DATABASE_URL_SYNC=postgresql+psycopg2://revold:revold_dev_only@localhost:5432/revold \
        poetry run alembic upgrade head
    poetry run pytest adapters/persistence/tests/test_catalog_repository_integration.py
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest
from revold_testing.catalog_factories import ProductFactory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from adapters_persistence.catalog.repository import PostgresProductRepository
from core_catalog.domain import Category, Money, Product, ProductVariant

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
        # Isola cada teste: começa sempre de tabelas vazias em vez de
        # depender de dados deixados por uma rodada anterior.
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


class TestSaveAndGetProduct:
    async def test_roundtrip_preserva_decimal_e_variantes(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        product = Product(
            sku="CAM-001",
            name="Camiseta Básica",
            category=camisetas,
            price=Money(Decimal("79.90")),
            variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
            images=["https://example.com/a.jpg"],
        )
        await repository.save_product(product)

        reloaded = await repository.get_product("CAM-001")
        assert reloaded is not None
        assert reloaded.price.amount == Decimal("79.90")
        assert reloaded.category.slug == "camisetas"
        assert len(reloaded.variants) == 1
        assert reloaded.variants[0].sku == "CAM-001-P"

    async def test_atualizar_produto_que_ja_tem_variante_nao_gera_conflito_de_pk(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        # Este é o caso que quebrava antes da correção de save_product
        # (recriar as variantes do zero gerava INSERT antes do DELETE do
        # órfão, dentro do mesmo flush, colidindo na primary key) — só
        # aparece contra SQL de verdade, o fake em memória não pega.
        product = Product(
            sku="CAM-001",
            name="Camiseta Básica",
            category=camisetas,
            price=Money(Decimal("79.90")),
            variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
        )
        await repository.save_product(product)

        updated = Product(
            sku="CAM-001",
            name="Camiseta Básica",
            category=camisetas,
            price=Money(Decimal("89.90")),
            variants=[
                ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=False),
                ProductVariant(sku="CAM-001-M", size="M", color="Branco", in_stock=True),
            ],
        )
        await repository.save_product(updated)  # não deve levantar IntegrityError

        reloaded = await repository.get_product("CAM-001")
        assert reloaded is not None
        assert reloaded.price.amount == Decimal("89.90")
        variants_by_sku = {v.sku: v for v in reloaded.variants}
        assert variants_by_sku["CAM-001-P"].in_stock is False
        assert variants_by_sku["CAM-001-M"].in_stock is True

    async def test_remover_variante_via_save_product_apaga_a_linha_de_verdade(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        product = Product(
            sku="CAM-001",
            name="Camiseta Básica",
            category=camisetas,
            price=Money(Decimal("79.90")),
            variants=[
                ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True),
                ProductVariant(sku="CAM-001-M", size="M", color="Branco", in_stock=True),
            ],
        )
        await repository.save_product(product)

        without_m = Product(
            sku="CAM-001",
            name="Camiseta Básica",
            category=camisetas,
            price=Money(Decimal("79.90")),
            variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
        )
        await repository.save_product(without_m)

        reloaded = await repository.get_product("CAM-001")
        assert reloaded is not None
        assert [v.sku for v in reloaded.variants] == ["CAM-001-P"]
        assert await repository.find_variant_owner("CAM-001-M") is None


class TestListProductsContraSqlDeVerdade:
    async def test_ordena_por_preco_via_order_by_real(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        barato = Product(
            sku="CAM-BARATO", name="Camiseta Barata", category=camisetas, price=Money(Decimal("29.90")), variants=[]
        )
        caro = Product(
            sku="CAM-CARO", name="Camiseta Cara", category=camisetas, price=Money(Decimal("199.90")), variants=[]
        )
        await repository.save_product(caro)
        await repository.save_product(barato)

        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, sort="price_asc"
        )
        assert total == 2
        assert [p.sku for p in items] == ["CAM-BARATO", "CAM-CARO"]

    async def test_filtra_por_variante_via_exists_real(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        await repository.save_product(
            Product(
                sku="CAM-001",
                name="Camiseta Listrada",
                category=camisetas,
                price=Money(Decimal("50")),
                variants=[
                    ProductVariant(sku="CAM-001-P-BR", size="P", color="Branco", in_stock=True),
                    ProductVariant(sku="CAM-001-M-BR", size="M", color="Branco", in_stock=True),
                ],
            )
        )
        await repository.save_product(
            Product(
                sku="CAL-001",
                name="Calça Jeans",
                category=camisetas,
                price=Money(Decimal("120")),
                variants=[ProductVariant(sku="CAL-001-38", size="38", color="Azul", in_stock=True)],
            )
        )

        # Tamanho sozinho: casa CAM-001 (tem variante "M").
        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, sizes=["M"]
        )
        assert total == 1
        assert items[0].sku == "CAM-001"

        # Tamanho + cor precisam casar a MESMA variante — CAM-001 não tem
        # nenhuma variante "M"/Azul (a "M" é Branco), então não deve casar.
        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, sizes=["M"], colors=["Azul"]
        )
        assert total == 0

        # Já "38"/Azul é a variante real de CAL-001.
        items, total = await repository.list_products(
            category_slug=None, page=1, page_size=10, sizes=["38"], colors=["Azul"]
        )
        assert total == 1
        assert items[0].sku == "CAL-001"

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
                sku="CAL-001", name="Calça Jeans", category=camisetas, price=Money(Decimal("120")), variants=[]
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


class TestDeleteContraSqlDeVerdade:
    async def test_delete_product_remove_produto_e_variantes_de_verdade(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        await repository.save_product(
            Product(
                sku="CAM-001",
                name="Camiseta Básica",
                category=camisetas,
                price=Money(Decimal("79.90")),
                variants=[ProductVariant(sku="CAM-001-P", size="P", color="Branco", in_stock=True)],
            )
        )

        await repository.delete_product("CAM-001")

        assert await repository.get_product("CAM-001") is None
        # A variante some junto (cascade delete-orphan) — não fica linha
        # órfã em catalog_product_variants.
        assert await repository.find_variant_owner("CAM-001-P") is None

    async def test_delete_product_sku_inexistente_nao_levanta_erro(
        self, repository: PostgresProductRepository
    ) -> None:
        await repository.delete_product("NAO-EXISTE")  # idempotente, sem erro

    async def test_delete_category_remove_categoria_de_verdade(
        self, repository: PostgresProductRepository
    ) -> None:
        await repository.save_category(Category(slug="acessorios", name="Acessórios"))
        await repository.delete_category("acessorios")
        assert await repository.get_category("acessorios") is None


class TestFabricaDeDadosContraPostgresReal:
    """Combina as duas práticas: dado gerado por fábrica (Faker), não
    fixture limpa escrita à mão, rodando contra SQL de verdade — o tipo de
    combinação que pega problema de precisão/encoding que nem o fake em
    memória nem uma fixture "CAM-001"/"Camiseta Básica" testariam."""

    async def test_lote_de_produtos_realistas_faz_roundtrip_sem_perder_precisao(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        produtos = [ProductFactory(category=camisetas) for _ in range(15)]
        for produto in produtos:
            await repository.save_product(produto)

        for produto in produtos:
            reloaded = await repository.get_product(produto.sku)
            assert reloaded is not None
            # Decimal com centavos "quebrados" (a fábrica gera R$xx,37 etc,
            # não só valores redondos) — confirma que NUMERIC(10,2) no
            # Postgres não perde precisão no caminho de ida e volta.
            assert reloaded.price.amount == produto.price.amount
            assert reloaded.name == produto.name
            assert {v.sku for v in reloaded.variants} == {v.sku for v in produto.variants}

    async def test_produto_com_nome_unicode_e_descricao_vazia_faz_roundtrip(
        self, repository: PostgresProductRepository, camisetas: Category
    ) -> None:
        produto = ProductFactory(category=camisetas, name="Vestido Midi Ção 🎉", description="")
        await repository.save_product(produto)

        reloaded = await repository.get_product(produto.sku)
        assert reloaded is not None
        assert reloaded.name == "Vestido Midi Ção 🎉"
        assert reloaded.description == ""
