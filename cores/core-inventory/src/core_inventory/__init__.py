"""core-inventory: bounded context de controle de estoque.

Mantém o nível de estoque por SKU (variante de produto): quantidade
fisicamente disponível e quantidade reservada (comprometida com um
carrinho em checkout, mas ainda não confirmada — ver ADR-0005, checkout
manual via WhatsApp). Depende apenas dos próprios SKUs; não importa
core_catalog nem core_cart (ADR-0002) — a orquestração entre eles vive no
api-gateway.
"""
