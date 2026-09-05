from __future__ import annotations

from decimal import Decimal

import pytest

from core_catalog.domain import CategoryNotFound, DuplicateSku, Money, ProductNotFound, ProductVariant
from core_catalog.use_cases import (
    CreateCategory,
    CreateProduct,
    GetProduct,
    ListCategories,
    ListProducts,
)


class TestListCategories:
    async def test_lista_categorias_unicas(self, fake_repository) -> None:
        result = await ListCategories(fake_repository).execute()
        slugs = {c.slug for c in result}
        assert slugs == {"camisetas", "calcas"}


class TestListProducts:
    async def test_lista_todos_sem_filtro(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute()
        assert result.total == 2
        assert len(result.items) == 2

    async def test_filtra_por_categoria(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(category_slug="camisetas")
        assert result.total == 1
        assert result.items[0].sku == "CAM-001"

    async def test_pagina_invalida_levanta_erro(self, fake_repository) -> None:
        with pytest.raises(ValueError):
            await ListProducts(fake_repository).execute(page=0)

    async def test_page_size_fora_do_intervalo_levanta_erro(self, fake_repository) -> None:
        with pytest.raises(ValueError):
            await ListProducts(fake_repository).execute(page_size=1000)


class TestGetProduct:
    async def test_retorna_produto_existente(self, fake_repository) -> None:
        product = await GetProduct(fake_repository).execute("CAM-001")
        assert product.name == "Camiseta Básica"

    async def test_produto_inexistente_levanta_not_found(self, fake_repository) -> None:
        with pytest.raises(ProductNotFound):
            await GetProduct(fake_repository).execute("NAO-EXISTE")

    async def test_is_available_considera_variantes_em_estoque(
        self, fake_repository
    ) -> None:
        product = await GetProduct(fake_repository).execute("CAM-001")
        assert product.is_available() is True


class TestCreateCategory:
    async def test_cria_categoria_nova(self, fake_repository) -> None:
        category = await CreateCategory(fake_repository).execute(slug="bolsas", name="Bolsas")
        assert category.slug == "bolsas"

        categorias = await ListCategories(fake_repository).execute()
        assert "bolsas" in {c.slug for c in categorias}


class TestCreateProduct:
    async def test_cria_produto_em_categoria_existente(self, fake_repository) -> None:
        product = await CreateProduct(fake_repository).execute(
            sku="VES-001",
            name="Vestido Floral",
            category_slug="camisetas",
            price=Money(Decimal("129.90")),
            variants=[ProductVariant(sku="VES-001-M", size="M", color="Floral", in_stock=True)],
        )
        assert product.sku == "VES-001"

        found = await GetProduct(fake_repository).execute("VES-001")
        assert found.name == "Vestido Floral"

    async def test_categoria_inexistente_levanta_category_not_found(
        self, fake_repository
    ) -> None:
        with pytest.raises(CategoryNotFound):
            await CreateProduct(fake_repository).execute(
                sku="VES-002",
                name="Vestido",
                category_slug="nao-existe",
                price=Money(Decimal("99.90")),
                variants=[],
            )

    async def test_sku_duplicado_levanta_duplicate_sku(self, fake_repository) -> None:
        with pytest.raises(DuplicateSku):
            await CreateProduct(fake_repository).execute(
                sku="CAM-001",
                name="Outra Camiseta",
                category_slug="camisetas",
                price=Money(Decimal("59.90")),
                variants=[],
            )
