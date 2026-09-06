from __future__ import annotations

import pytest
from revold_testing.store_settings_factories import StoreSettingsFactory

from core_store_settings.domain import StoreSettings


def _settings(**overrides) -> StoreSettings:
    defaults = dict(
        cnpj="",
        store_name="",
        contact_email="",
        contact_phone="",
        store_address="",
        low_stock_threshold=5,
    )
    defaults.update(overrides)
    return StoreSettings(**defaults)


def test_aceita_registro_vazio_com_limiar_padrao() -> None:
    settings = _settings()
    assert settings.cnpj == ""
    assert settings.low_stock_threshold == 5


def test_aceita_cnpj_mascarado_e_normaliza_para_so_digitos() -> None:
    settings = _settings(cnpj="12.345.678/0001-95")
    assert settings.cnpj_digits == "12345678000195"


def test_aceita_cnpj_so_digitos() -> None:
    settings = _settings(cnpj="12345678000195")
    assert settings.cnpj_digits == "12345678000195"


def test_rejeita_cnpj_com_numero_errado_de_digitos() -> None:
    with pytest.raises(ValueError):
        _settings(cnpj="123")


def test_rejeita_email_sem_arroba() -> None:
    with pytest.raises(ValueError):
        _settings(contact_email="nao-e-email")


def test_rejeita_limiar_negativo() -> None:
    with pytest.raises(ValueError):
        _settings(low_stock_threshold=-1)


class TestFabricaDeDados:
    def test_fabrica_gera_registro_totalmente_preenchido_e_valido(self) -> None:
        # Os testes acima usam `_settings()` (todo campo textual vazio por
        # padrão) — a fábrica é o inverso: gera os 6 campos preenchidos com
        # dado realista de uma vez, confirmando que "totalmente
        # preenchido" também passa por __post_init__ sem exceção alguma.
        settings = StoreSettingsFactory()
        assert len(settings.cnpj_digits) == 14
        assert settings.store_name
        assert "@" in settings.contact_email
        assert settings.low_stock_threshold >= 0

    def test_fabrica_gera_cnpjs_distintos_a_cada_chamada(self) -> None:
        a, b = StoreSettingsFactory(), StoreSettingsFactory()
        assert a.cnpj_digits != b.cnpj_digits
