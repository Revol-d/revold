"""Clientes de modelos no protocolo OpenAI: Azure OpenAI e endpoints compatíveis (DeepSeek).

- `chat.AzureOpenAIChat` e `chat.OpenAICompatibleChat`: geração de resposta;
- `embeddings.AzureOpenAIEmbeddings`: vetor de um texto;
- `messages.ChatTurn`: uma fala da conversa, sem vocabulário de negócio. Não faz I/O, por isso
  está em `pure_modules` do `unit.yaml`.

Não conhece assistente, catálogo nem produto. Quem traduz a conversa do domínio para `ChatTurn` é
a camada `adapters/llm/` do domínio `ai-assistant` (ADR-0011, ADR-0026).
"""

__all__ = ["chat", "embeddings", "messages"]
