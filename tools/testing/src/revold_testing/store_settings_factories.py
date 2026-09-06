"""Fábrica de dados (Factory Boy + Faker, locale pt_BR) para
`core_store_settings.domain.StoreSettings` (ADR-0019).

Faker "pt_BR" não traz um provider de CNPJ pronto — a fábrica gera 14
dígitos aleatórios (o domínio só valida a *quantidade* de dígitos, não o
dígito verificador oficial do CNPJ, ver `StoreSettings.__post_init__`), o
suficiente para exercitar o formato aceito sem inventar um algoritmo de
dígito verificador que o próprio domínio não checa.
"""
from __future__ import annotations

import factory
from faker import Faker

from core_store_settings.domain import StoreSettings

fake = Faker("pt_BR")


def _cnpj_digits() -> str:
    # `fake.unique` garante que duas chamadas nunca gerem o mesmo CNPJ na
    # mesma sessão de teste (ver test_fabrica_gera_cnpjs_distintos_a_cada_chamada).
    return str(fake.unique.random_number(digits=14, fix_len=True)).zfill(14)


class StoreSettingsFactory(factory.Factory):
    class Meta:
        model = StoreSettings

    cnpj = factory.LazyFunction(_cnpj_digits)
    store_name = factory.LazyFunction(lambda: fake.company())
    contact_email = factory.LazyFunction(lambda: fake.company_email())
    contact_phone = factory.LazyFunction(lambda: fake.phone_number())
    store_address = factory.LazyFunction(lambda: fake.address().replace("\n", ", "))
    low_stock_threshold = factory.LazyFunction(lambda: fake.random_int(min=0, max=20))
