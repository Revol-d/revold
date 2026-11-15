"""Núcleo de domínio de pagamento (ADR-0024).

Pix e cartão, atrás de uma porta única (`PaymentGateway`) — a mesma
progressão de todo o resto do projeto: porta → adapter fake (dev) →
adapter real validado em sandbox → adapter real com credencial de
produção. Cartão nunca é processado diretamente aqui: o adapter real usa
checkout hospedado do provedor (nunca recebe número de cartão), para não
puxar o projeto para escopo PCI-DSS.

`payments` não conhece `orders` (ADR-0002, bounded contexts não
se importam) — a ligação "cobrança confirmada → marcar pedido como pago"
é orquestração e vive no api-gateway (mesmo padrão de `cart`↔`orders`
na ADR-0023).
"""
