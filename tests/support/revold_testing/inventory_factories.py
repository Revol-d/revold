"""Fábrica de dados (Factory Boy + Faker, locale pt_BR) para
`revold_inventory.domain.StockLevel`.

O ponto de um `StockLevel` de teste gerado por fábrica em vez de sempre
`StockLevel(sku="X", quantity_on_hand=5)`: os testes existentes de
`inventory` (`tests/test_domain.py`) já cobrem as regras do domínio,
mas cada um com exatamente 1 exemplo numérico escolhido à mão — nenhum
confirma que a invariante (`quantity_available == quantity_on_hand -
quantity_reserved`) se sustenta para qualquer combinação válida de
quantidades, só para aquelas que alguém lembrou de escrever. A fábrica
gera `quantity_reserved` sempre como uma fração aleatória (mas válida) de
`quantity_on_hand`, então um teste que a chama N vezes vira, na prática,
um teste baseado em propriedade em vez de um exemplo fixo.
"""
from __future__ import annotations

import factory
from faker import Faker

from revold_inventory.domain import StockLevel

fake = Faker("pt_BR")

_SIZES = ["PP", "P", "M", "G", "GG"]
_COLORS = ["PRETO", "BRANCO", "AZUL", "VERDE", "VERMELHO"]


def _variant_sku() -> str:
    return f"{fake.unique.numerify(text='SKU-####')}-{fake.random_element(_SIZES)}-{fake.random_element(_COLORS)}"


class StockLevelFactory(factory.Factory):
    class Meta:
        model = StockLevel

    sku = factory.LazyFunction(_variant_sku)
    quantity_on_hand = factory.LazyFunction(lambda: fake.random_int(min=1, max=200))

    @factory.lazy_attribute
    def quantity_reserved(self) -> int:
        # Nunca excede quantity_on_hand (StockLevel.__post_init__ rejeitaria)
        # — mas também não é sempre 0, senão nenhum teste de
        # quantity_available/reserve/release exercitaria o caso comum de
        # "já tem reserva parcial". mypy enxerga `self.quantity_on_hand`
        # como o descriptor `LazyFunction` declarado na classe, não como o
        # int resolvido em tempo de build — limitação conhecida de
        # factory_boy com `@lazy_attribute` cruzando campos.
        return fake.random_int(min=0, max=self.quantity_on_hand)  # type: ignore[arg-type]
