# `revold_ai_assistant`

Assistente de IA: busca por similaridade no catálogo indexado e resposta com LangGraph.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `postgres`, `openai`

## O que faz

Casos de uso `AskAssistant` e `IndexProduct` (ADR-0011), as portas `LLMProvider` e `ProductIndex`, e os adapters: `adapters/llm/` (dev, Azure OpenAI, DeepSeek e a factory `build_llm_provider`) e `adapters/postgres/` (índice vetorial em pgvector). A pasta `evals/` guarda o dataset comportamental e o LLM-as-judge (ADR-0012).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não lê o catálogo.** Quem lê o catálogo e manda indexar é o produto (`revold_ecommerce.application.catalog_indexing`).
- **Não lê `LLM_PROVIDER`.** O app entrega um `LLMSettings` pronto.

## Testes

```powershell
uv run pytest libs/domains/ai-assistant/tests -q
```
