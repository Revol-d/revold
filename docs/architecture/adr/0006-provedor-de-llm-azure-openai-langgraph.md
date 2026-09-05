# ADR-0006: Provedor de LLM — Azure OpenAI + LangGraph, porta para DeepSeek

**Status:** Aceito

## Contexto
`core-ai-assistant` usa LangChain para RAG e agora também LangGraph para orquestração de fluxo/estado do assistente. O modelo usado hoje é Azure OpenAI. DeepSeek é candidato futuro por custo, mas é um modelo ainda não avaliado quanto à qualidade e à confiabilidade para este uso, e processa dados fora do Azure — o que levanta uma questão de LGPD (onde os dados são processados) a avaliar antes de qualquer troca.

## Decisão
`core-ai-assistant` define uma porta `LLMProvider` (chat completion + embeddings, para o RAG com pgvector). A implementação atual (`adapters/external/azure-openai`) usa Azure OpenAI. LangGraph é usado dentro do core para orquestrar o fluxo do agente (estado da conversa, decisão de quando escalar para atendimento humano via WhatsApp), independente de qual `LLMProvider` está por trás.

DeepSeek (ou qualquer outro provedor futuro) entra como uma segunda implementação da mesma porta, só adotada em produção depois de:
1. Avaliação própria de qualidade/latência para o caso de uso (FAQ e recomendação de produto, não geração aberta).
2. Confirmação de onde os dados são processados, e se isso é compatível com o tratamento de dados pessoais já feito (LGPD).

## Consequências
- Trocar de provedor de LLM não deveria exigir mudar `core-ai-assistant`, só o adapter e a configuração.
- Fica registrado que "mais barato" (DeepSeek) não é decisão só de custo — depende de validação de qualidade e de compliance antes de ir para produção.
