"""Fábrica de dados (Factory Boy + Faker, locale pt_BR) para
`revold_notification.domain.Notification`.
"""
from __future__ import annotations

import factory
from faker import Faker

from revold_notification.domain import Notification

fake = Faker("pt_BR")

_EVENT_TYPES = ["new_checkout", "low_stock"]


class NotificationFactory(factory.Factory):
    class Meta:
        model = Notification

    event_type = factory.LazyFunction(lambda: fake.random_element(_EVENT_TYPES))
    message = factory.LazyFunction(lambda: fake.sentence(nb_words=8))
