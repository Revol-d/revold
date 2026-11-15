# `revold_ecommerce`

Produto de e-commerce: o que cruza os domínios da loja.

- **Tipo:** product · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `ai-assistant`, `catalog`, `identity`, `inventory`, `notification`, `orders`, `payments`, `store-settings`, `platform`, `postgres`

## O que faz

| Módulo de `application/` | O que faz |
|---|---|
| `stock` | publica `stock.low` quando o disponível cai abaixo do limiar e dá baixa no estoque das linhas de um pedido pago |
| `catalog_indexing` | lê o catálogo e indexa para o assistente, em lote ou um SKU |
| `event_handlers` | o que fazer com cada evento consumido pelo `event-worker` e o encaminhamento a webhooks |
| `seed` | o seed semântico de catálogo, estoque e configuração (ADR-0022) |

Em `adapters/`, `database` junta os modelos de todos os domínios com tabela no Postgres num `metadata` só: é o que o `env.py` das migrações e o teste `tests/test_migrations_match_models.py` comparam com o banco. Domínio novo com tabela entra na lista dele, no mesmo PR da migração.

Fora do pacote: `contracts/api/` (os contratos OpenAPI da API; a lista de rotas é conferida pelo teste de contrato do api-gateway) e `migrations/` (o histórico Alembic do banco da loja).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não lê ambiente nem monta adapter.** Recebe portas; quem monta é o app.
- **Não guarda regra de um contexto só.** Regra de carrinho mora em `cart`, de estoque em `inventory`. Aqui só entra o que precisa de dois ou mais.

## Testes

```powershell
uv run pytest products/ecommerce/tests -q
```
