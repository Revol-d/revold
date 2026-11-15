"""Fábricas de dados (Factory Boy + Faker, locale pt_BR) para os objetos de
domínio de `revold_cart`.

`revold_cart.domain.Money` é um value object próprio do core (não o mesmo de
`revold_catalog.domain.Money` — bounded contexts não compartilham modelo de
domínio, ver ADR-0002), então ganha sua própria fábrica em vez de reusar
`revold_testing.catalog_factories.MoneyFactory`.
"""
from __future__ import annotations

import factory
from faker import Faker

from revold_cart.domain import Cart, CartItem, Money

fake = Faker("pt_BR")


def _sku(prefix: str = "SKU") -> str:
    return f"{prefix}-{fake.unique.numerify(text='####')}"


class MoneyFactory(factory.Factory):
    class Meta:
        model = Money

    amount = factory.LazyFunction(
        lambda: fake.pydecimal(left_digits=3, right_digits=2, positive=True, min_value=1)
    )
    currency = "BRL"


class CartItemFactory(factory.Factory):
    class Meta:
        model = CartItem

    sku = factory.LazyFunction(_sku)
    # fake.sentence() sempre termina com "." — nome de produto não usa ponto.
    name = factory.LazyFunction(lambda: fake.sentence(nb_words=3).rstrip("."))
    variant_label = factory.LazyFunction(
        lambda: f"{fake.random_element(['PP', 'P', 'M', 'G', 'GG'])} / {fake.color_name()}"
    )
    unit_price = factory.SubFactory(MoneyFactory)
    quantity = factory.LazyFunction(lambda: fake.random_int(min=1, max=5))


class CartFactory(factory.Factory):
    class Meta:
        model = Cart

    cart_id = factory.LazyFunction(lambda: fake.uuid4())
    currency = "BRL"

    @factory.post_generation
    def items(self, create, extracted, **kwargs):  # noqa: ANN001
        # Sem argumento: carrinho vem vazio (comportamento default do
        # dataclass). Passar um int (`CartFactory(items=3)`) povoa o
        # carrinho com N itens gerados pela CartItemFactory — evita todo
        # teste de "carrinho com item" ter que chamar add_item() à mão.
        count = extracted if isinstance(extracted, int) else 0
        for _ in range(count):
            item = CartItemFactory()
            self.add_item(
                sku=item.sku,
                name=item.name,
                variant_label=item.variant_label,
                unit_price=item.unit_price,
                quantity=item.quantity,
            )
