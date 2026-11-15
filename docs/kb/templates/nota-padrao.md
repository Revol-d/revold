---
tags: []
status: ativo
escopo: <plataforma | ecommerce>
resumo: <uma linha — o que esta nota responde; sem dois-pontos-espaço no meio>
cobre: [<caminhos de código que esta nota descreve>]
---

# <Título da nota>

> <opcional: para que serve / quando ler esta nota>

## <Seção>

- Conteúdo **atômico**: um assunto por nota. Se crescer demais, quebre em notas menores.
- Links para outras notas com caminho relativo, ex.: [ambiente local](../ambiente-local-no-windows.md).
- Decisões e gotchas levam **data** (AAAA-MM). Marque incertezas com `(confirmar)`.
- Gotcha tem três partes: o **sintoma** que a pessoa vê, a **causa** e a **solução**.

<!--
Convenções de frontmatter:
  tags   — lista curta em kebab-case: [dominio, frontend, runbook, decisao, gotchas...]
  status — ativo | rascunho | obsoleto
  escopo — plataforma: vale para o monorepo inteiro. ecommerce: só faz sentido no produto da loja.
  resumo — 1 linha escaneável (a IA lê o metadado sem abrir o corpo). Evite ": " (quebra YAML).
  cobre  — caminhos de código que esta nota descreve. É o que permite perceber que a nota
           envelheceu: se um desses caminhos mudou depois da nota, releia a nota.
           - Prefira o caminho mais ESTREITO que ainda representa a nota. `cobre: [apps]` muda em
             todo commit e vira ruído; `cobre: [apps/ecommerce/api-gateway/Dockerfile]` só muda
             quando importa.
           - `cobre: []` = a nota deliberadamente não deriva de código (glossário de negócio).

Nunca ponha em nota: valor de variável de ambiente, credencial, token, connection string, ID de
recurso de nuvem, caminho absoluto de máquina ou e-mail de pessoa. Cite o NOME da variável.

Nota nova sem linha em ../README.md fica invisível.
-->
