<!--
Padrão de interação (ver AGENTS.md): NÃO use emojis/ícones; NÃO credite IA como co-autora.
A DIVULGAÇÃO de uso de IA (seção "Uso de IA" abaixo) permanece: divulgar uso não é creditar autoria.
Título do PR em Conventional Commits: ele vira a mensagem do commit na main.
-->

## Resumo da mudança
<!-- O que mudou e por quê? Seja objetivo. -->

## Issue
Closes #

## Escopo da mudança
### Dentro do escopo neste PR
-
-

### Fora do escopo neste PR
-
-

## Unidades impactadas
<!-- O id do unit.yaml de cada uma. O ideal é uma só (CONTRIBUTING 4.1). `uv run dev affected` lista. -->
-

## Uso de IA
- [ ] Não houve uso relevante de IA
- [ ] Houve uso de IA para análise / decomposição
- [ ] Houve uso de IA para geração de código
- [ ] Houve uso de IA para geração de testes
- [ ] Houve uso de IA para documentação

### Se houve uso relevante de IA, responda (texto, não checkbox; ver CONTRIBUTING 4.9)
- Ferramenta utilizada:
- Arquivos ou trechos gerados pela IA:
- Teste existente que mudou neste PR, e por quê (ou "nenhum"):
- O que roda fora do pytest (container, banco, pagamento, e-mail, WhatsApp, Azure) e como foi verificado (cole a saída):
- Barreiras tocadas (`noqa`, `type: ignore`, `nosec`, `except` amplo, CI, hooks, CODEOWNERS, `unit.yaml`) e por quê (ou "nenhuma"):
- Responsável pela revisão final:

## Arquitetura e segurança
- [ ] O código está na unidade e na camada certas (docs/ARQUITETURA.md)
- [ ] `uv run dev check` verde, sem editar `.importlinter` ou `CODEOWNERS` à mão
- [ ] Variável de ambiente lida só no `settings.py` do app
- [ ] Autenticação/autorização foram avaliadas
- [ ] Validação de entrada e tratamento de erro foram avaliados
- [ ] Não há segredo ou dado pessoal indevido no código ou no log
- [ ] Dependências novas foram avaliadas e estão no `unit.yaml` e no `pyproject.toml`
- [ ] Dado pessoal novo foi sinalizado (LGPD, docs/security/README.md)

### Impactos de segurança / risco
-

## Testes executados
- [ ] unitários
- [ ] integração (Postgres/Redis de verdade)
- [ ] contrato (`-m contract`), se mudou rota ou contrato
- [ ] eval do assistente (`-m eval`)
- [ ] E2E (`make test-e2e`)
- [ ] pilha local de pé (`make dev`)

### Evidências
<!-- O comando que você rodou e o fim da saída. "Deve passar" não é evidência. -->
- Comando e resultado:
- O que NÃO foi verificado, e por quê:

## Versão
- [ ] Nenhum `src/` de unidade mudou
- [ ] O `src/` de uma unidade mudou e a versão dela subiu (`uv run dev bump <unidade> <parte>`), com o `uv.lock`
- [ ] O `src/` de uma unidade mudou, e nenhum app que a usa tem release ainda (bump não exigido, CONTRIBUTING 7.2)
- [ ] Este é um PR de release (`uv run dev release <app> <parte>`)

## Build, deploy e rollback
<!-- Só se a mudança vai virar release. Responda as perguntas da seção 8.2 do CONTRIBUTING. -->
- Muda schema do banco? Migração e ordem:
- Muda variável de ambiente ou segredo?
- Muda contrato de API ou formato de evento?
- Plano de volta:

## Checklist final do autor
- [ ] Li e revisei o diff inteiro na aba "Files changed"
- [ ] O PR resolve o problema da issue, e só ele
- [ ] O PR tem até ~400 linhas de código escrito, ou a descrição explica por que não (recomendação)
- [ ] Os testes estão proporcionais ao risco
- [ ] README da unidade, `.env.example` e docs atualizados quando necessário
- [ ] Conhecimento que custou para achar virou nota na KB (AGENTS.md)

## Checklist do revisor
- [ ] Contexto suficiente para revisar
- [ ] Código na unidade e na camada certas; fronteiras respeitadas
- [ ] Regra de negócio nova não ficou dentro de rota da API ou de tarefa do worker (mora no domínio ou no produto)
- [ ] Testes e evidências suficientes
- [ ] Segurança e operação avaliadas
- [ ] Testes existentes não foram enfraquecidos para passar (assert, skip, xfail, marcador)
- [ ] O que roda fora do pytest tem evidência de execução real ou documentação oficial
- [ ] O fluxo do CONTRIBUTING foi seguido (sem atalho de versão, deploy ou gate)
