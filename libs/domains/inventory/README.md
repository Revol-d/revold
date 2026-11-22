# `revold_inventory`

Estoque por SKU: entrada, reserva, liberação e baixa.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `azure-sql`

## O que faz

A entidade `StockLevel` e os casos de uso de receber, reservar, liberar e dar baixa em estoque, a porta `InventoryRepository` e o adapter `adapters/azure_sql/`.

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não publica evento de estoque baixo.** Quem decide e publica é o produto (`revold_ecommerce.application.stock`).
- **Não conhece pedido.** A baixa por linha de pedido é orquestração do produto.

## Testes

```powershell
uv run pytest libs/domains/inventory/tests -q
```
