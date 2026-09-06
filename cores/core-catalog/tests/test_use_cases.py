from __future__ import annotations

from decimal import Decimal

import pytest

from core_catalog.domain import (
    CategoryHasProducts,
    CategoryNotFound,
    DuplicateSku,
    DuplicateVariantSku,
    Money,
    ProductNotFound,
    ProductVariant,
    VariantNotFound,
)
from core_catalog.use_cases import (
    AddProductVariant,
    CreateCategory,
    CreateProduct,
    DeleteCategory,
    DeleteProduct,
    GetProduct,
    ListCategories,
    ListProducts,
    RemoveProductVariant,
    UpdateProduct,
    UpdateProductVariant,
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

    async def test_busca_por_substring_no_nome_case_insensitive(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(search_query="jeans")
        assert result.total == 1
        assert result.items[0].sku == "CAL-001"

    async def test_busca_sem_correspondencia_retorna_vazio(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(search_query="vestido")
        assert result.total == 0

    async def test_ordena_por_preco_crescente(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(sort="price_asc")
        assert [p.sku for p in result.items] == ["CAM-001", "CAL-001"]

    async def test_ordena_por_preco_decrescente(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(sort="price_desc")
        assert [p.sku for p in result.items] == ["CAL-001", "CAM-001"]

    async def test_sort_invalido_levanta_erro(self, fake_repository) -> None:
        with pytest.raises(ValueError):
            await ListProducts(fake_repository).execute(sort="preco_qualquer")

    async def test_filtra_por_tamanho(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(sizes=["M"])
        assert result.total == 1
        assert result.items[0].sku == "CAM-001"

    async def test_filtra_por_cor(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(colors=["Azul"])
        assert result.total == 1
        assert result.items[0].sku == "CAL-001"

    async def test_tamanho_e_cor_exigem_a_mesma_variante(self, fake_repository) -> None:
        # CAM-001 tem uma variante "P"/Branco e outra "M"/Branco — nenhuma é
        # "M" e "Azul" ao mesmo tempo, então não deve casar.
        result = await ListProducts(fake_repository).execute(sizes=["M"], colors=["Azul"])
        assert result.total == 0

    async def test_filtro_sem_correspondencia_retorna_vazio(self, fake_repository) -> None:
        result = await ListProducts(fake_repository).execute(sizes=["GG"])
        assert result.total == 0


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

    async def test_variante_com_sku_de_outro_produto_levanta_duplicate_variant_sku(
        self, fake_repository
    ) -> None:
        # CAM-001-P-BR já é variante de CAM-001 — SKU de variante é único
        # globalmente (mesma chave usada pelo core-inventory), não só dentro
        # de um produto, então criar OUTRO produto reaproveitando esse SKU
        # de variante tem que ser rejeitado.
        with pytest.raises(DuplicateVariantSku):
            await CreateProduct(fake_repository).execute(
                sku="VES-003",
                name="Vestido",
                category_slug="camisetas",
                price=Money(Decimal("99.90")),
                variants=[
                    ProductVariant(sku="CAM-001-P-BR", size="P", color="Branco", in_stock=True)
                ],
            )


class TestUpdateProduct:
    async def test_atualiza_so_os_campos_enviados(self, fake_repository) -> None:
        original = await GetProduct(fake_repository).execute("CAM-001")

        updated = await UpdateProduct(fake_repository).execute(
            "CAM-001", name="Camiseta Básica (Nova Coleção)"
        )

        assert updated.name == "Camiseta Básica (Nova Coleção)"
        # Campos não enviados continuam iguais.
        assert updated.price == original.price
        assert updated.description == original.description
        assert updated.variants == original.variants

    async def test_atualiza_preco_e_categoria(self, fake_repository) -> None:
        updated = await UpdateProduct(fake_repository).execute(
            "CAM-001", price=Money(Decimal("89.90")), category_slug="calcas"
        )
        assert updated.price == Money(Decimal("89.90"))
        assert updated.category.slug == "calcas"

    async def test_clear_original_price_remove_preco_original(self, fake_repository) -> None:
        await UpdateProduct(fake_repository).execute(
            "CAM-001", original_price=Money(Decimal("99.90"))
        )
        updated = await UpdateProduct(fake_repository).execute(
            "CAM-001", clear_original_price=True
        )
        assert updated.original_price is None

    async def test_produto_inexistente_levanta_not_found(self, fake_repository) -> None:
        with pytest.raises(ProductNotFound):
            await UpdateProduct(fake_repository).execute("NAO-EXISTE", name="X")

    async def test_categoria_nova_inexistente_levanta_category_not_found(
        self, fake_repository
    ) -> None:
        with pytest.raises(CategoryNotFound):
            await UpdateProduct(fake_repository).execute("CAM-001", category_slug="nao-existe")


class TestAddProductVariant:
    async def test_adiciona_variante_nova(self, fake_repository) -> None:
        nova = ProductVariant(sku="CAM-001-G-BR", size="G", color="Branco", in_stock=True)
        updated = await AddProductVariant(fake_repository).execute("CAM-001", nova)

        assert nova in updated.variants
        assert len(updated.variants) == 3

    async def test_produto_inexistente_levanta_not_found(self, fake_repository) -> None:
        variante = ProductVariant(sku="X-1", size="U", color="Preto", in_stock=True)
        with pytest.raises(ProductNotFound):
            await AddProductVariant(fake_repository).execute("NAO-EXISTE", variante)

    async def test_sku_de_variante_duplicado_levanta_duplicate_variant_sku(
        self, fake_repository
    ) -> None:
        repetida = ProductVariant(sku="CAM-001-P-BR", size="P", color="Branco", in_stock=True)
        with pytest.raises(DuplicateVariantSku):
            await AddProductVariant(fake_repository).execute("CAM-001", repetida)

    async def test_sku_de_variante_de_outro_produto_levanta_duplicate_variant_sku(
        self, fake_repository
    ) -> None:
        # CAL-001-38 já é variante de CAL-001 — não pode ser reaproveitado
        # como variante nova de CAM-001 (SKU de variante é único
        # globalmente, não só dentro do produto-alvo).
        de_outro_produto = ProductVariant(
            sku="CAL-001-38", size="38", color="Azul", in_stock=True
        )
        with pytest.raises(DuplicateVariantSku):
            await AddProductVariant(fake_repository).execute("CAM-001", de_outro_produto)


class TestUpdateProductVariant:
    async def test_atualiza_so_o_campo_enviado(self, fake_repository) -> None:
        updated = await UpdateProductVariant(fake_repository).execute(
            "CAM-001", "CAM-001-M-BR", in_stock=True
        )
        variant = next(v for v in updated.variants if v.sku == "CAM-001-M-BR")
        assert variant.in_stock is True
        assert variant.size == "M"  # não enviado, permanece igual
        assert variant.color == "Branco"  # não enviado, permanece igual

    async def test_atualiza_size_e_color(self, fake_repository) -> None:
        updated = await UpdateProductVariant(fake_repository).execute(
            "CAM-001", "CAM-001-P-BR", size="PP", color="Cinza"
        )
        variant = next(v for v in updated.variants if v.sku == "CAM-001-P-BR")
        assert variant.size == "PP"
        assert variant.color == "Cinza"

    async def test_sku_da_variante_nunca_muda(self, fake_repository) -> None:
        updated = await UpdateProductVariant(fake_repository).execute(
            "CAM-001", "CAM-001-P-BR", size="PP"
        )
        skus = {v.sku for v in updated.variants}
        assert "CAM-001-P-BR" in skus

    async def test_produto_inexistente_levanta_not_found(self, fake_repository) -> None:
        with pytest.raises(ProductNotFound):
            await UpdateProductVariant(fake_repository).execute(
                "NAO-EXISTE", "CAM-001-P-BR", in_stock=False
            )

    async def test_variante_inexistente_levanta_variant_not_found(self, fake_repository) -> None:
        with pytest.raises(VariantNotFound):
            await UpdateProductVariant(fake_repository).execute(
                "CAM-001", "NAO-EXISTE-SKU", in_stock=False
            )


class TestRemoveProductVariant:
    async def test_remove_variante_existente(self, fake_repository) -> None:
        updated = await RemoveProductVariant(fake_repository).execute("CAM-001", "CAM-001-M-BR")
        skus = {v.sku for v in updated.variants}
        assert "CAM-001-M-BR" not in skus
        assert len(updated.variants) == 1

    async def test_produto_inexistente_levanta_not_found(self, fake_repository) -> None:
        with pytest.raises(ProductNotFound):
            await RemoveProductVariant(fake_repository).execute("NAO-EXISTE", "CAM-001-P-BR")

    async def test_variante_inexistente_levanta_variant_not_found(self, fake_repository) -> None:
        with pytest.raises(VariantNotFound):
            await RemoveProductVariant(fake_repository).execute("CAM-001", "NAO-EXISTE-SKU")

    async def test_remover_todas_as_variantes_e_permitido(self, fake_repository) -> None:
        # Um produto pode ficar sem nenhuma variante (peça única, sem grade
        # de tamanho/cor) — não é um estado inválido.
        await RemoveProductVariant(fake_repository).execute("CAM-001", "CAM-001-P-BR")
        updated = await RemoveProductVariant(fake_repository).execute("CAM-001", "CAM-001-M-BR")
        assert updated.variants == []


class TestDeleteProduct:
    async def test_remove_produto_existente(self, fake_repository) -> None:
        await DeleteProduct(fake_repository).execute("CAM-001")
        with pytest.raises(ProductNotFound):
            await GetProduct(fake_repository).execute("CAM-001")

    async def test_produto_inexistente_levanta_not_found(self, fake_repository) -> None:
        with pytest.raises(ProductNotFound):
            await DeleteProduct(fake_repository).execute("NAO-EXISTE")


class TestDeleteCategory:
    async def test_categoria_inexistente_levanta_not_found(self, fake_repository) -> None:
        with pytest.raises(CategoryNotFound):
            await DeleteCategory(fake_repository).execute("nao-existe")

    async def test_categoria_com_produtos_levanta_category_has_products(
        self, fake_repository
    ) -> None:
        # "camisetas" tem CAM-001 no fixture sample_products.
        with pytest.raises(CategoryHasProducts):
            await DeleteCategory(fake_repository).execute("camisetas")

    async def test_categoria_sem_produtos_e_removida(self, fake_repository) -> None:
        await CreateCategory(fake_repository).execute(slug="acessorios", name="Acessórios")
        await DeleteCategory(fake_repository).execute("acessorios")
        categorias = await ListCategories(fake_repository).execute()
        assert "acessorios" not in {c.slug for c in categorias}
