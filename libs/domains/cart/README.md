# `revold_cart`

Carrinho de compras: itens, quantidades e total.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

A entidade `Cart` e os casos de uso de adicionar, alterar, remover e limpar itens, a porta `CartRepository` e o adapter `adapters/redis/` (carrinho serializado em JSON, com expiração).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não conhece catálogo nem estoque.** Preço e nome do item chegam por parâmetro; reservar estoque é orquestração do app.
- **Não fecha pedido.** Isso é do domínio `orders`.

## Testes

```powershell
uv run pytest libs/domains/cart/tests -q
```
