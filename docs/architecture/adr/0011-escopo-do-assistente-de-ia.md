# ADR-0011: Escopo do assistente de IA (core-ai-assistant)

**Status:** Aceito

## Contexto

ADR-0006 já decidiu o provedor de LLM (Azure OpenAI + LangGraph, porta aberta
para DeepSeek), mas nunca chegou a definir *o que* o assistente faz de fato —
`core-ai-assistant` continuava só com um docstring de intenção. Como não há
prazo e o objetivo de longo prazo é o framework reutilizável da empresa (ver
avaliação de planejamento), decidi o escopo do MVP para poder implementar o
resto do vertical slice sem ficar bloqueado esperando uma definição de
produto que hoje não tem outro dono.

## Decisão

**Escopo do MVP**: um assistente de perguntas e respostas sobre o catálogo
(não um vendedor autônomo, não um agente que fecha pedido sozinho). Ele:

1. Recebe uma pergunta do cliente (+ histórico da conversa).
2. Busca produtos relevantes no catálogo via RAG (embeddings + pgvector,
   como já previa o ADR-0006).
3. Responde usando o `LLMProvider` configurado, com os produtos encontrados
   como contexto.
4. Decide se deve **escalar para atendimento humano via WhatsApp** — hoje
   uma heurística simples de palavras-chave de intenção de compra ("quero
   comprar", "fechar pedido", "como pago" etc.). Isso é deliberadamente
   provisório: um classificador de intenção via LLM é o passo natural
   assim que houver um provedor real (Azure OpenAI) em produção, mas não
   faz sentido pedir isso de um provider dev que não chama modelo nenhum.

**Orquestração via LangGraph** (grafo de 3 nós: `retrieve` → `generate` →
`decide_escalation`), dentro do próprio `core-ai-assistant` — LangGraph aqui
é biblioteca de domínio do core (equivalente a `Decimal` no core-catalog),
não infraestrutura web, então não fere a regra de core não depender de
FastAPI (ADR-0002).

**Índice do catálogo é responsabilidade do próprio core-ai-assistant**
(porta `ProductIndex`, implementação Postgres+pgvector), não do
core-catalog — os dois cores nunca se importam (ADR-0002). Popular esse
índice a partir do catálogo é orquestração cross-core, e por isso vive em
`workers/catalog-indexer` (o primeiro uso real do diretório `workers/`),
não dentro de nenhum dos dois cores. O worker também é exposto como
endpoint administrativo (`POST /api/assistant/reindex`, papel STAFF/ADMIN)
para rodar sob demanda sem depender de um worker Celery já no ar, e como
tarefa Celery (`celery_app.py`, broker Redis, já é dependência do projeto)
para agendar reindexação periódica em produção.

**Adapters, mesmo sem credencial (ver seção 3.3 da avaliação de
planejamento — construir e testar sem os serviços externos liberados):**
- `DevLLMProvider` (`adapters/external/ai/dev_llm_provider.py`): embeddings
  pseudo-aleatórios determinísticos (mesmo texto → mesmo vetor, via seed de
  hash) e resposta de completion baseada em regra simples — não chama
  nenhum modelo de verdade, mas exercita toda a porta `LLMProvider` e o
  fluxo do LangGraph de ponta a ponta em teste.
- `AzureOpenAILLMProvider` (`adapters/external/ai/azure_openai_provider.py`):
  implementação real via `langchain-openai` (`AzureChatOpenAI` +
  `AzureOpenAIEmbeddings`). Código completo, mas **não testado contra a API
  de verdade** nesta sessão — não há credencial Azure OpenAI disponível.
  Trocar para produção é só configuração (`LLM_PROVIDER=azure-openai` +
  `AZURE_OPENAI_*`), igual ao padrão já usado em `core-identity`.

**Dimensão do embedding fixada em 1536** (mesma do `text-embedding-3-small`
da OpenAI/Azure OpenAI, provável escolha de produção) — tanto o
`DevLLMProvider` quanto a coluna `vector` do Postgres usam essa dimensão,
para que trocar de provider não exija nova migração.

## Consequências

- O assistente **não** fecha pedido sozinho — ele só aponta o cliente para
  a conversa manual com a Nick (reaproveitando `core_communication` via
  orquestração no api-gateway, mesmo padrão do checkout do carrinho).
- A heurística de escalonamento por palavra-chave vai gerar falsos
  negativos/positivos — aceitável para o MVP, mas deve ser revisitada
  quando houver provedor de LLM real em produção (usar o próprio modelo
  para classificar intenção, em vez de regex).
- Reindexar o catálogo é uma operação manual (endpoint admin) ou agendada
  (Celery) — não há reindexação automática a cada mudança de produto
  ainda; para o volume de catálogo da Nick hoje isso é aceitável, mas deve
  ser revisitado (ex.: reindexar ao salvar produto) se o catálogo crescer
  ou mudar com muita frequência.
- `pgvector` (extensão Postgres) precisa existir no banco — a imagem
  `pgvector/pgvector:pg16` já usada no `docker-compose.yml` desde o
  scaffold inicial já traz a extensão; a migração só precisa habilitá-la
  (`CREATE EXTENSION IF NOT EXISTS vector`).
