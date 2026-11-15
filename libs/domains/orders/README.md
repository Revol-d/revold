# `revold_orders`

Pedidos: criação a partir do carrinho e transições de pagamento e de atendimento.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `postgres`

## O que faz

A entidade `Order` com as linhas e os dois status, os casos de uso de criar, consultar, listar e mudar status (ADR-0023), a porta `OrderRepository` e o adapter `adapters/postgres/`.

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não cobra.** Cobrança é do domínio `payments`.
- **Não dá baixa no estoque.** Isso é orquestração do produto.

## Testes

```powershell
uv run pytest libs/domains/orders/tests -q
```
