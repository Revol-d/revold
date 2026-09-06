"""Fábricas de dados (Factory Boy + Faker, locale pt_BR) para os objetos de
domínio de `core_catalog`.

Por quê isto existe: fixtures escritas à mão (`Product(sku="CAM-001", ...)`)
são fáceis de ler mas todas "limpas" — o mesmo formato de SKU, nomes sem
acento, sempre 1-2 variantes. Isso não exercita casos de borda plausíveis
(nome com acento/emoji, descrição vazia, produto sem variante, preço com
centavos quebrados) a menos que alguém lembre de escrever cada um à mão.
Estas fábricas geram dados realistas por padrão e permitem sobrescrever só
o campo que o teste quer controlar — ex.:

    ProductFactory(name="Vestido Midi Ção 🎉", description="")

Convenção: fábricas ficam em `tools/testing` (pacote `revold_testing`) em
vez de dentro de `cores/core-catalog/tests/` porque outros cores (ex.
core-inventory, que referencia SKU de variante) também podem precisar gerar
um Product/ProductVariant plausível em teste — ver a seção "Framework
Proprietário" da descrição do monorepo.
"""
from __future__ import annotations

import factory
from faker import Faker

from core_catalog.domain import Category, Money, Product, ProductVariant

fake = Faker("pt_BR")

_SIZES = ["PP", "P", "M", "G", "GG"]


def _sku(prefix: str) -> str:
    return f"{prefix}-{fake.unique.numerify(text='####')}"


class MoneyFactory(factory.Factory):
    class Meta:
        model = Money

    # left_digits=3 -> até R$999,99, mais que suficiente pra roupa e ainda
    # gera valores com centavos "quebrados" (R$79,37, não só R$79,90).
    amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True, min_value=1)
    )
    currency = "BRL"


class CategoryFactory(factory.Factory):
    class Meta:
        model = Category

    slug = factory.LazyFunction(lambda: fake.unique.slug())
    name = factory.LazyFunction(lambda: fake.word().capitalize())


class ProductVariantFactory(factory.Factory):
    class Meta:
        model = ProductVariant

    sku = factory.LazyFunction(lambda: _sku("VAR"))
    size = factory.LazyFunction(lambda: fake.random_element(_SIZES))
    color = factory.LazyFunction(lambda: fake.color_name())
    in_stock = True


class ProductFactory(factory.Factory):
    class Meta:
        model = Product

    sku = factory.LazyFunction(lambda: _sku("SKU"))
    # fake.sentence() sempre termina com ".", nome de produto não usa ponto.
    name = factory.LazyFunction(lambda: fake.sentence(nb_words=3).rstrip("."))
    category = factory.SubFactory(CategoryFactory)
    price = factory.SubFactory(MoneyFactory)
    variants = factory.LazyFunction(lambda: [ProductVariantFactory(), ProductVariantFactory()])
    description = factory.LazyFunction(lambda: fake.paragraph(nb_sentences=2))
    images = factory.LazyFunction(lambda: [fake.image_url()])
