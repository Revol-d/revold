"""Dado de demonstração ("seed semântico") de `revold_store_settings` — ver
ADR-0022 e o módulo irmão `revold_catalog.seed` para o raciocínio completo.

`StoreSettings` é um registro único (ADR-0019) — sem isto preenchido, a
tela `/configuracoes` do admin-dashboard (que a Nick de fato usa) também
fica vazia durante qualquer avaliação/demo, do mesmo jeito que o catálogo
ficava sem `revold_catalog.seed`. CNPJ e telefone abaixo são placeholders
óbvios (não correspondem a uma empresa real) só pra passar na validação de
formato (`revold_store_settings.domain.StoreSettings.__post_init__`) e
preencher a tela — troque pelos dados reais da Nick assim que ela tiver
CNPJ (ver ADR-0005, motivo de o checkout ainda ser manual via WhatsApp).
"""
from __future__ import annotations

from revold_store_settings.domain import StoreSettings

DEMO_SETTINGS = StoreSettings(
    cnpj="00.000.000/0001-00",
    store_name="Nick Moda",
    contact_email="contato@nickmoda.com.br",
    contact_phone="(11) 91234-5678",
    store_address="Rua das Palmeiras, 123 — São Paulo, SP",
    # Baixo de propósito pro seed do catálogo (revold_catalog.seed) já
    # deixar um par de variantes abaixo do limiar — ver VES-003/CAD-003 —
    # e a Nick conseguir ver o alerta de estoque baixo em /estoque sem
    # precisar vender nada primeiro.
    low_stock_threshold=5,
)
