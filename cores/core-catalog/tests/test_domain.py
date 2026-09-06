"""Testes diretos dos objetos de domínio (sem repositório/caso de uso).

Estes casos existiam como validação no código (`Money.__post_init__`) mas
sem nenhum teste cobrindo — só apareceriam quebrados em produção, o
problema exato que motivou esta rodada (dado limpo demais no teste esconde
regra de negócio sem cobertura)."""
from __future__ import annotations

import pytest
from revold_testing.catalog_factories import CategoryFactory, MoneyFactory, ProductFactory

from core_catalog.domain import Money, ProductVariant


class TestMoney:
    def test_valor_negativo_e_rejeitado(self) -> None:
        with pytest.raises(ValueError, match="não pode ser negativo"):
            Money(amount=-1)

    def test_valor_zero_e_aceito(self) -> None:
        # Zero não é negativo — produto em liquidação a custo zero é uma
        # decisão de negócio válida, não deveria ser bloqueada aqui.
        Money(amount=0)

    def test_moeda_com_menos_de_3_letras_e_rejeitada(self) -> None:
        with pytest.raises(ValueError, match="ISO 4217"):
            Money(amount=10, currency="R$")

    def test_moeda_com_mais_de_3_letras_e_rejeitada(self) -> None:
        with pytest.raises(ValueError, match="ISO 4217"):
            Money(amount=10, currency="BRLL")

    def test_fabrica_gera_valor_com_centavos_realistas(self) -> None:
        # Regressão pro tipo de bug que só aparece com dado "sujo": preço
        # sempre redondo (R$79,90) no teste manual nunca pegaria erro de
        # arredondamento Decimal — a fábrica gera centavos variados.
        money = MoneyFactory()
        assert money.amount >= 1
        # 2 casas decimais exatas (Decimal, não float) — garante que a
        # fábrica não gerou algo como 79.9999.
        assert money.amount.as_tuple().exponent == -2


class TestProduct:
    def test_is_available_com_todas_variantes_esgotadas_e_falso(self) -> None:
        product = ProductFactory(
            variants=[
                ProductVariant(sku="A", size="P", color="Preto", in_stock=False),
                ProductVariant(sku="B", size="M", color="Preto", in_stock=False),
            ]
        )
        assert product.is_available() is False

    def test_is_available_sem_nenhuma_variante_e_falso(self) -> None:
        # any([]) é False em Python — mas vale um teste explícito: produto
        # sem variante (ex. logo depois de remover a última, ver
        # RemoveProductVariant) não deve aparecer como "disponível".
        product = ProductFactory(variants=[])
        assert product.is_available() is False

    def test_nome_com_acento_e_emoji_e_preservado_sem_normalizacao(self) -> None:
        # Unicode "de verdade" (não só ASCII) é exatamente o tipo de dado
        # que uma fixture escrita à mão nunca testa por acidente.
        product = ProductFactory(name="Vestido Midi Ção 🎉")
        assert product.name == "Vestido Midi Ção 🎉"

    def test_descricao_vazia_e_um_valor_valido(self) -> None:
        # Description tem default "" — confirma que string vazia explícita
        # também não é rejeitada em nenhum lugar do domínio.
        product = ProductFactory(description="")
        assert product.description == ""

    def test_sem_imagem_e_um_valor_valido(self) -> None:
        product = ProductFactory(images=[])
        assert product.images == []


class TestCategory:
    def test_fabrica_gera_slug_e_nome_nao_vazios(self) -> None:
        category = CategoryFactory()
        assert category.slug
        assert category.name

    def test_categorias_distintas_tem_slugs_distintos(self) -> None:
        # fake.unique.slug() -- confirma que a fábrica realmente usa o
        # gerador "unique" do Faker (evita colisão silenciosa entre testes
        # que criam várias categorias na mesma sessão de pytest).
        a, b = CategoryFactory(), CategoryFactory()
        assert a.slug != b.slug
