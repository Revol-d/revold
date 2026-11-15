# ADR-0026: DeepSeek como LLM_PROVIDER de chat — embeddings continuam na Azure OpenAI

**Status:** Aceito

## Contexto

O Samuel tirou uma API key da DeepSeek e perguntou como funciona a troca de
modelo de IA hoje (`LLM_PROVIDER`, ADR-0006/ADR-0011), notando corretamente
que a DeepSeek é bem diferente da Azure OpenAI:

- **Azure OpenAI** exige provisionar um recurso ("deployment") antes de
  chamar — `AzureChatOpenAI`/`AzureOpenAIEmbeddings` recebem
  `azure_deployment` como configuração fixa (`AZURE_OPENAI_DEPLOYMENT`,
  `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`).
- **DeepSeek** expõe uma API compatível com o formato OpenAI: a chave de
  API já é suficiente, e o nome do modelo (`deepseek-chat`,
  `deepseek-reasoner`, ou o que estiver disponível no momento) é só um
  parâmetro passado em cada chamada — não há "deployment" para provisionar
  antes.

## Decisão

**`LLM_PROVIDER=deepseek` (novo) usa dois provedores ao mesmo tempo, não
um só — decisão explícita do Samuel ("deixa o embed pra Azure e o lllm pro
deepseek"):**

- `complete()` (chat) fala com a **DeepSeek**, via `ChatOpenAI` do
  `langchain-openai` apontado para `DEEPSEEK_BASE_URL`
  (`https://api.deepseek.com`, API compatível com o formato OpenAI).
- `embed()` (embeddings, usado pelo índice semântico de produtos/RAG)
  continua na **Azure OpenAI**, reaproveitando exatamente as mesmas
  credenciais/deployment que `AzureOpenAILLMProvider` já usa
  (`AZURE_OPENAI_ENDPOINT`/`AZURE_OPENAI_API_KEY`/
  `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`) — a DeepSeek não expõe um endpoint
  de embeddings compatível com o formato OpenAI, então não há alternativa
  hoje.

Implementado como um único adapter novo,
`adapters_external/ai/deepseek_llm_provider.py::DeepSeekLLMProvider`, que
implementa a porta `core_ai_assistant.ports.LLMProvider` (a mesma porta de
sempre — quem chama `complete()`/`embed()` não sabe nem precisa saber que
as duas chamadas vão para provedores diferentes por baixo). Selecionado
via `LLM_PROVIDER=deepseek` em `adapters_external/ai/factory.py`, mesmo
padrão de `PAYMENT_PROVIDER`/`AUTH_PROVIDER`/`NOTIFICATION_PROVIDER`
(ADR-0011): trocar de provedor é mudar variável de ambiente, nunca
importar um adapter diferente manualmente.

`get_llm_provider()` valida duas listas de variáveis separadamente e falha
com `NotImplementedError` explicando qual falta:

1. `DEEPSEEK_API_KEY` + `DEEPSEEK_MODEL` (chat).
2. `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` +
   `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` (embeddings) — as três mesmas
   variáveis que `LLM_PROVIDER=azure-openai` já usa, mas aqui só a parte de
   embeddings é necessária (`AZURE_OPENAI_DEPLOYMENT`, o deployment de
   *chat* da Azure, não é usado quando `LLM_PROVIDER=deepseek`).

## Nome do modelo da DeepSeek não tem valor default de propósito

Ao pesquisar para escrever este adapter (nomes de modelo mudam com
frequência na DeepSeek, diferente da Azure onde o "deployment" é escolhido
uma vez e fica estável), encontrei indicação de que os nomes mais
conhecidos (`deepseek-chat`/`deepseek-reasoner`) estariam sendo
substituídos por nomes novos por volta de meados de 2026, segundo a
documentação oficial (`api-docs.deepseek.com`) e uma fonte terceira. Como
meu conhecimento sobre a API da DeepSeek vem majoritariamente de pesquisa
feita depois do meu corte de treinamento (portanto com confiança menor que
o resto deste código), optei por **não** hardcodar nenhum nome de modelo
como default — `DEEPSEEK_MODEL` fica obrigatório em `.env.example`, com um
comentário apontando para conferir o nome atual em
`https://api-docs.deepseek.com/` antes de configurar. Isso espelha por que
`AZURE_OPENAI_DEPLOYMENT` também não tem default (esse é sempre um recurso
específico da conta de cada um). `DEEPSEEK_BASE_URL`, em contraste, tem
default (`https://api.deepseek.com`) porque essa parte é estável e
documentada de forma consistente por múltiplas fontes.

## Sobre a validação

Mesmo padrão de ADR-0011/ADR-0012/ADR-0024/ADR-0025: testes `respx`
(`adapters/external/tests/test_deepseek_llm_provider.py`) interceptam as
chamadas HTTP que o SDK da OpenAI faz por baixo do `langchain-openai` —
tanto para a DeepSeek (`complete()`) quanto para a Azure OpenAI
(`embed()`) — validando contra o formato documentado publicamente, nunca
contra a API real (nenhuma credencial real disponível no ambiente onde
isto foi escrito). Um teste (`test_embed_usa_a_azure_openai_nao_o_deepseek`)
existe especificamente para provar que `embed()` nunca chama a DeepSeek:
só a rota da Azure é mockada, e uma chamada indevida à DeepSeek derrubaria
o teste por rota não mockada.

A validação final contra a API de verdade da DeepSeek só pode ser feita
pelo Samuel, com a chave que ele já tirou, confirmando também qual nome de
modelo está disponível hoje.

## Consequências

- `LLM_PROVIDER=deepseek` fica disponível como terceira opção ao lado de
  `dev` (mock) e `azure-openai` (chat + embed, ambos na Azure) — nenhuma
  mudança na porta `LLMProvider` nem em quem a consome
  (`core-ai-assistant`).
- Rodar com `LLM_PROVIDER=deepseek` exige credenciais de **dois**
  provedores ao mesmo tempo (DeepSeek para chat, Azure OpenAI para
  embeddings) — documentado em `.env.example` e nas mensagens de erro do
  factory, para não ser uma surpresa na hora de configurar.
- Se no futuro a DeepSeek (ou outro provedor) passar a oferecer
  embeddings compatíveis, a troca fica isolada dentro de
  `DeepSeekLLMProvider.embed()` — não precisa de mudança na porta nem em
  quem chama.

## Validação

```
poetry run pytest adapters/external/tests/test_deepseek_llm_provider.py -v   # 6 passed
poetry run ruff check adapters/external/src/adapters_external/ai/deepseek_llm_provider.py adapters/external/src/adapters_external/ai/factory.py   # All checks passed
poetry run mypy adapters/external/src/adapters_external/ai/deepseek_llm_provider.py adapters/external/src/adapters_external/ai/factory.py   # Success: no issues found
poetry run pytest   # 434 passed, 52 skipped (+ o 1 falho pré-existente de test_metrics_endpoint.py, que precisa de Postgres/Docker rodando — não relacionado a esta mudança)
```
