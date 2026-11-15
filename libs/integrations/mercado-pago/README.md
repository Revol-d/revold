# `revold_mercado_pago`

Cliente do Mercado Pago: cria e consulta pagamento e confere a assinatura do webhook.

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

- `client.MercadoPagoClient`: `create_pix_payment` e `get_payment`, devolvendo o JSON da API;
- `webhook_signature.is_valid_webhook_signature`: confere o `x-signature` (webhooks v2). Sem I/O, por isso está em `pure_modules`.

## O que NÃO faz

- **Não conhece cobrança, pedido nem status de negócio.** A tradução para o domínio é de `adapters/gateways/` do domínio `payments` (ADR-0024).
- **Não implementa cartão.** Só Pix, pelo mesmo motivo registrado na ADR-0024.

## Testes

```powershell
uv run pytest libs/integrations/mercado-pago/tests -q
```
