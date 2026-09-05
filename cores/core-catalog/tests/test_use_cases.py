from __future__ import annotations

import pytest

from core_catalog.domain import ProductNotFound
from core_catalog.use_cases import GetProduct, ListCategories, ListProducts


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
