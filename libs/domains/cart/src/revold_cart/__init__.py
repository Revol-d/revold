"""`cart`: bounded context de carrinho de compras.

Identificado por um cart_id opaco (não exige login). Não importa
revold_catalog nem revold_communication diretamente (ADR-0002) — a composição
com esses outros cores acontece no api-gateway.
"""
