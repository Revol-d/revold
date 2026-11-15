# `revold_catalog`

Catálogo de produtos: categorias, produtos, variantes e imagens.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `postgres`, `azure-blob`

## O que faz

As entidades `Product`, `ProductVariant` e `Category`, os casos de uso de leitura e de escrita do catálogo, as portas `ProductRepository` e `MediaStorage`, e os adapters: `adapters/postgres/` (com busca full-text, ADR-0014) e `adapters/media/` (disco local, Azure Blob e a factory `build_media_storage`, ADR-0015). `seed.py` declara o catálogo de demonstração (ADR-0022).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não controla estoque.** A quantidade por SKU é do domínio `inventory`.
- **Não indexa para o assistente.** Isso é do produto.

## Testes

```powershell
uv run pytest libs/domains/catalog/tests -q
```
