from __future__ import annotations

from revold_store_settings.application.use_cases import GetStoreSettings, UpdateStoreSettings


async def test_get_devolve_registro_vazio_com_limiar_padrao_quando_nada_configurado(
    fake_repository,
) -> None:
    settings = await GetStoreSettings(fake_repository).execute(default_low_stock_threshold=7)
    assert settings.store_name == ""
    assert settings.low_stock_threshold == 7


async def test_update_cria_registro_quando_nao_existia(fake_repository) -> None:
    settings = await UpdateStoreSettings(fake_repository).execute(
        default_low_stock_threshold=5,
        cnpj="12.345.678/0001-95",
        store_name="Nick Roupas",
        contact_email="contato@nick.com.br",
    )
    assert settings.store_name == "Nick Roupas"
    assert settings.contact_email == "contato@nick.com.br"
    assert settings.low_stock_threshold == 5  # não informado, cai no default

    persisted = await fake_repository.get()
    assert persisted == settings


async def test_update_altera_so_o_campo_informado_preservando_o_resto(fake_repository) -> None:
    await UpdateStoreSettings(fake_repository).execute(
        default_low_stock_threshold=5,
        store_name="Nick Roupas",
        contact_phone="+55 11 90000-0000",
    )

    updated = await UpdateStoreSettings(fake_repository).execute(
        default_low_stock_threshold=5,
        low_stock_threshold=10,
    )

    assert updated.store_name == "Nick Roupas"
    assert updated.contact_phone == "+55 11 90000-0000"
    assert updated.low_stock_threshold == 10
