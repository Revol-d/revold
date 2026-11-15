from __future__ import annotations

from decimal import Decimal

import pytest
from revold_testing.cart_factories import CartFactory, CartItemFactory

from revold_cart.domain import Cart, CartItemNotFound, Money


def test_add_item_novo():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2


def test_add_item_existente_soma_quantidade():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=1)
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 3


def test_total_soma_subtotais():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=2)
    cart.add_item(sku="B", name="Calça", variant_label="38", unit_price=Money(Decimal("100")), quantity=1)
    assert cart.total().amount == Decimal("200")


def test_update_item_quantity():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=1)
    cart.update_item_quantity("A", 5)
    assert cart.items[0].quantity == 5


def test_update_item_inexistente_levanta_erro():
    cart = Cart(cart_id="c1")
    with pytest.raises(CartItemNotFound):
        cart.update_item_quantity("NAO-EXISTE", 1)


def test_remove_item():
    cart = Cart(cart_id="c1")
    cart.add_item(sku="A", name="Camiseta", variant_label="M", unit_price=Money(Decimal("50")), quantity=1)
    cart.remove_item("A")
    assert cart.items == []


def test_money_nao_soma_moedas_diferentes():
    with pytest.raises(ValueError):
        Money(Decimal("10"), "BRL") + Money(Decimal("10"), "USD")


class TestFabricasDeDados:
    """Casos que uma fixture escrita à mão (sempre "Camiseta"/"M", preço
    redondo) não exercitaria por acidente — mesmo raciocínio de
    `core-catalog/tests/test_domain.py` (ver ADR-0012)."""

    def test_nome_e_variant_label_com_acento_sao_preservados(self) -> None:
        item = CartItemFactory(name="Vestido Midi Ção 🎉", variant_label="GG / Azul-Marinho")
        assert item.name == "Vestido Midi Ção 🎉"
        assert item.variant_label == "GG / Azul-Marinho"

    def test_fabrica_gera_preco_com_centavos_realistas(self) -> None:
        item = CartItemFactory()
        # 2 casas decimais exatas (Decimal, não float) — mesma checagem de
        # regressão que `catalog_factories.MoneyFactory` já tem.
        assert item.unit_price.amount.as_tuple().exponent == -2

    def test_cart_factory_com_items_povoa_carrinho_e_total_bate_com_subtotais(self) -> None:
        # Gera um carrinho com 3 itens aleatórios (SKU, preço e quantidade
        # diferentes a cada execução) e confirma a invariante — não só o
        # exemplo fixo (2 itens, preços redondos) que os testes acima já
        # cobrem, mas qualquer combinação plausível que a fábrica gerar.
        cart = CartFactory(items=3)
        assert len(cart.items) == 3
        esperado = sum((item.subtotal().amount for item in cart.items), start=Decimal("0"))
        assert cart.total().amount == esperado

    def test_cart_factory_sem_argumento_vem_vazio(self) -> None:
        cart = CartFactory()
        assert cart.items == []
        assert cart.total().amount == Decimal("0")
