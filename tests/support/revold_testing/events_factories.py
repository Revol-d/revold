"""Fábrica de dados (Factory Boy + Faker, locale pt_BR) para
`revold_platform.events.domain.DomainEvent`.
"""
from __future__ import annotations

import factory
from faker import Faker

from revold_platform.events.domain import DomainEvent

fake = Faker("pt_BR")

# Amostra pequena e real dos nomes de evento que já existem no código (ver
# apps/ecommerce/event-worker/src/event_worker/dispatch.py) — gerar um nome
# aleatório tipo "<palavra qualquer>.<palavra qualquer>" passaria na
# validação de domínio mas não representaria nenhum evento real do
# sistema.
_EVENT_NAMES = ["product.updated", "checkout.created", "stock.low", "catalog.reindex_requested"]


class DomainEventFactory(factory.Factory):
    class Meta:
        model = DomainEvent

    name = factory.LazyFunction(lambda: fake.random_element(_EVENT_NAMES))
    payload = factory.LazyFunction(lambda: {"sku": f"SKU-{fake.unique.numerify(text='####')}"})
