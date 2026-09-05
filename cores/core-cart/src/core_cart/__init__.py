"""core-cart: bounded context de carrinho de compras.

Identificado por um cart_id opaco (não exige login). Não importa
core_catalog nem core_communication diretamente (ADR-0002) — a composição
com esses outros cores acontece no api-gateway.
"""
