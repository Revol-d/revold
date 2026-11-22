---
tags: [decisao, plataforma, persistencia, azure-sql]
status: implementado
escopo: plataforma
resumo: Postgres e substituido por Azure SQL Database como unico backend de persistencia, via o mesmo padrao de fabrica/provider ja usado em LLM, pagamento, notificacao e midia
cobre: [libs/integrations/azure-sql, libs/domains/*/adapters/azure_sql, products/ecommerce/migrations_azure_sql, deploy/terraform/modules/azure-sql, docker-compose.yml, .github/workflows/ci.yml]
---

# 0032 — Migração de Postgres para Azure SQL Database

**Data:** 2026-11 (migração completa, Fases 0 a 7)
**Revisa:** [0006](0006-provedor-de-llm-azure-openai-langgraph.md) (só a parte de armazenamento
vetorial — pgvector), [0014](0014-busca-full-text-tsvector.md) (full-text inteira — mecanismo
trocado), e a premissa "sempre Postgres, sem provedor de nuvem a trocar" de
[0016](0016-api-key-rate-limit-webhook-outbound.md), [0019](0019-core-store-settings-configuracao-da-loja.md),
[0023](0023-core-orders-gestao-de-pedidos.md) e [0024](0024-core-payments-pix-e-cartao.md).
Os contextos de negócio dessas quatro ADRs continuam valendo — só a persistência mudou de técnica.

## Contexto

Persistência era a única categoria de integração do repositório sem o padrão de fábrica
(`Settings` + `build_X()` + variável de ambiente) já usado por LLM, pagamento, notificação e
mídia: todo `get_*_repository` em `dependencies.py` retornava `Postgres*Repository(session)`
direto, com comentários nas ADR-0016/0019/0023/0024 dizendo "sempre Postgres, não há provedor de
nuvem a trocar". Isso parou de ser verdade quando o Azure SQL Database passou a ter (confirmado,
Nov/2026) um free tier real (100.000 vCore-segundos + 32GB/mês por banco, até 10 bancos grátis por
subscription) — diferente do Postgres Flexible Server, que não tem free tier algum — e suporte
nativo a tipo `VECTOR` + índice DiskANN, substituto direto do pgvector usado pelo `ai-assistant`
(ADR-0006).

## Opções

1. **Manter Postgres** — zero risco de migração, mas sem free tier: custo de infraestrutura
   recorrente desde o primeiro cliente piloto.
2. **Suporte dual permanente** (os dois bancos coexistindo para sempre, escolhido por variável de
   ambiente) — flexibilidade de hospedagem, mas dobra o código de adapter, migração e CI para
   sempre, sem benefício contínuo depois que a escolha for feita uma vez.
3. **Troca única — escolhida.** Valida o Azure SQL por domínio com os dois bancos coexistindo só
   durante a migração, depois apaga o código do Postgres inteiro (adapters, migrações, integração,
   container do CI, dependências, módulo Terraform). Sem dado em produção quando a migração
   começou, o custo de errar era só reescrever código apagado, não migrar dado real.

## Decisão

Opção 3. Persistência passou a seguir o mesmo padrão de fábrica das outras integrações
substituíveis — mas, diferente delas, **sem permanecer substituível**: depois do corte (Fase 6) e
da limpeza (Fase 7), só existe um provedor (`revold_azure_sql`), sem variável
`PERSISTENCE_PROVIDER` nem ramificação de provider em nenhuma camada.

### Achados técnicos que mudaram o desenho original

Verificados contra ferramenta real (containers locais + bancos Azure SQL reais, criados e
apagados só para teste) em vez de assumidos:

- **`VECTOR` nativo exige SQL Server 2025 (17.x) no motor, não 2022.** O Azure SQL Database (PaaS)
  já tinha o tipo disponível antes disso — motor "em caixa" (container de CI/dev) só alcançou em
  2025. Descoberto rodando a migração de verdade contra `2022-latest` ("Cannot find data type
  VECTOR", erro 2715).
- **Full-text do SQL Server não faz accent-folding sozinho.** Colação accent-insensitive resolve
  igualdade de string comum, mas `CONTAINSTABLE`/`FREETEXT` ignoram a colação. Mecanismo que
  funciona: coluna computada persistida com `TRANSLATE` tirando acento à mão, com o termo de busca
  passando pela mesma normalização no adapter (`libs/domains/catalog/adapters/azure_sql/`).
- **Índice vetorial (`CREATE VECTOR INDEX`, DiskANN) com suporte a escrita contínua só está GA no
  Azure SQL Database real.** Mesmo um SQL Server 2025 em caixa cria a versão antiga do índice, que
  torna a tabela somente-leitura assim que o índice existe (erro 42231 em qualquer
  INSERT/UPDATE/DELETE) — `ALLOW_STALE_VECTOR_INDEX`, a válvula de escape documentada pela
  Microsoft, nem é reconhecida nessa build. Decisão: **não criar o índice via migração** —
  `VECTOR_DISTANCE` funciona sem índice (scan completo), idêntico em qualquer ambiente. Criar o
  índice fica para uma tarefa operacional futura, quando a versão DML-friendly estiver disponível
  de forma confiável fora do Azure SQL Database PaaS.
- **`String`/`Text` do SQLAlchemy não são portáveis para texto livre no dialeto mssql** (achado de
  revisão, `dmourans`, PR #14): viram `VARCHAR`/`TEXT`, sujeitos à colação padrão do servidor
  (`SQL_Latin1_General_CP1_CI_AS`) — caractere fora do CP1252 (emoji, a maior parte do CJK) é
  trocado por `?` ao gravar, **sem erro nenhum**. Toda coluna de texto livre (nome, descrição,
  endereço, rótulo de variante/API key) usa `Unicode`/`UnicodeText` (`NVARCHAR`/`NTEXT`); colunas
  estruturadas/ASCII por contrato (ids, hashes, status, moedas, códigos) continuam `String`/`Text`.
- **A imagem oficial do SQL Server não tem Full-Text Search instalado nem cria o banco sozinha.**
  `mssql-server-fts` mora no repositório específico do produto (`mssql-server-2025`), não no
  repositório "prod" que a imagem já traz, e só pode ser instalado antes do primeiro start do
  `sqlservr` — não funciona via `docker exec` num container já rodando. Resolvido com uma imagem
  própria (`deploy/docker/mssql/`, usada em CI e em `docker-compose.yml`) que builda o pacote e usa
  um entrypoint que cria o banco `revold` sozinho.
- **`pyodbc`/`aioodbc` exigem o driver ODBC instalado como biblioteca de sistema**, não só o pacote
  Python — sem isso, os containers do `api-gateway`/`event-worker`/`catalog-indexer` (base
  `python:3.12-slim`, Debian) sobem mas qualquer conexão com o banco falha. Instalado no `base`
  stage dos três Dockerfiles.
- **Comparador de tipo customizado necessário no Alembic** para o tipo `Vector`: o dialeto mssql
  reflete `VECTOR(n)` como `VARBINARY(n*4+8)` (não reconhece o tipo nativo), e sem um
  `compare_type` que trata isso como "sem diferença", `alembic revision --autogenerate` e o teste
  `test_migrations_match_models.py` acusariam mudança em toda rodada, mesmo sem nada ter mudado.

## Consequências

- `PERSISTENCE_PROVIDER` deixou de existir. Todo `build_<domínio>_repository(session)` monta
  direto o adapter `azure_sql` — sem parâmetro de provider, sem `if/else` de import.
- `libs/integrations/postgres/`, `adapters/postgres/` dos sete domínios,
  `products/ecommerce/migrations/` (trilha Postgres) e o módulo Terraform `postgres` foram
  apagados. `alembic-azure-sql.ini` virou `alembic.ini` (o único que resta);
  `migrations_azure_sql/` manteve o nome (convenção do repo: integração leva nome da tecnologia
  concreta, mesmo sendo a única — ver `redis`, `smtp`, `whatsapp`).
- CI: um job de testes só (`tests`), contra um container próprio de SQL Server 2025 com Full-Text
  Search — obrigatório, não mais opcional (sem Postgres como alternativa, não há mais sentido em
  "não-bloqueante").
- `docker-compose.yml`: serviço `mssql` é o único banco, sem `profiles` opt-in.
- Terraform: `azurerm_mssql_server` + `azurerm_mssql_database` (serverless, `GP_S_Gen5_2`) sem VNet
  dedicada (diferente do Postgres Flexible Server) — PaaS público com firewall de IP. O free tier
  em si (`use_free_limit`) ainda não é exposto pelo provider `azurerm` (~> 3.116, checado v3.117.1)
  — precisa ser ativado manualmente uma vez após o primeiro `apply` (Portal ou `az sql db update`)
  até o provider alcançar o recurso.
- Criar o índice vetorial (`CREATE VECTOR INDEX`) fica como dívida técnica deliberada, documentada
  em `libs/domains/ai-assistant/adapters/azure_sql/models.py` — revisitar quando a versão
  DML-friendly do índice estiver disponível de forma confiável fora do Azure SQL Database PaaS.
