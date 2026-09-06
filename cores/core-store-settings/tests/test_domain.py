from __future__ import annotations

import pytest

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
