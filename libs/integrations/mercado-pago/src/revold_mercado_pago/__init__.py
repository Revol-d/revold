"""Cliente do Mercado Pago: cria e consulta pagamento e confere a assinatura do webhook.

- `client.MercadoPagoClient`: fala com a API (`/v1/payments`). Faz chamada de rede.
- `webhook_signature.is_valid_webhook_signature`: confere o `x-signature` do webhook. Não faz
  I/O, por isso está em `pure_modules` do `unit.yaml`.

Não conhece cobrança, pedido nem status de negócio: devolve o que a API devolve. A tradução para
o domínio é da camada `adapters/gateways/` do domínio `payments` (ADR-0024).
"""

__all__ = ["client", "webhook_signature"]
