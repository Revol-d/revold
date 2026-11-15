# `revold_openai`

Clientes de modelos no protocolo OpenAI: Azure OpenAI e endpoints compatíveis (DeepSeek).

- **Tipo:** integration · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** nenhuma unidade

## O que faz

- `chat.AzureOpenAIChat` e `chat.OpenAICompatibleChat`: geração de resposta;
- `embeddings.AzureOpenAIEmbeddings`: vetor de um texto;
- `messages.ChatTurn`: uma fala da conversa. Sem I/O, por isso está em `pure_modules`.

## O que NÃO faz

- **Não conhece assistente, catálogo nem produto.** Quem traduz a conversa do domínio é `adapters/llm/` do domínio `ai-assistant` (ADR-0011, ADR-0026).
- **Não escolhe o provedor.** A escolha é da factory do domínio, com a configuração que o app entrega.

## Testes

```powershell
uv run pytest libs/integrations/openai/tests -q
```
