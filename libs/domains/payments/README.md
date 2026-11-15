# `revold_payments`

Pagamentos: cobrança por Pix e cartão e reconciliação por webhook.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `postgres`, `mercado-pago`

## O que faz

A entidade `Charge`, os casos de uso de criar cobrança e confirmar pagamento (ADR-0024), as portas `PaymentGateway` e `ChargeRepository`, e os adapters: `adapters/gateways/` (fake, Mercado Pago e a factory `build_payment_gateway`) e `adapters/postgres/`.

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não muda o status do pedido.** Quem liga pagamento confirmado a pedido e estoque é o app, com o produto.
- **Não fala com a API do Mercado Pago diretamente.** Usa o cliente de `libs/integrations/mercado-pago`.

## Testes

```powershell
uv run pytest libs/domains/payments/tests -q
```
