# `revold_store_settings`

Configuração da loja editável pelo admin: dados cadastrais e limiar de estoque baixo.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `postgres`

## O que faz

A entidade `StoreSettings` com a validação dos campos, os casos de uso de ler e salvar (ADR-0019), a porta `StoreSettingsRepository` e o adapter `adapters/postgres/`. `seed.py` declara a configuração de demonstração (ADR-0022).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não lê `LOW_STOCK_THRESHOLD`.** O valor padrão chega por parâmetro, vindo do `settings.py` do app.

## Testes

```powershell
uv run pytest libs/domains/store-settings/tests -q
```
