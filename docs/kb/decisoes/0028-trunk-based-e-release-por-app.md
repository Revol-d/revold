---
tags: [decisao, git, branch, ci, release, processo]
status: decidido-nao-executado
escopo: plataforma
resumo: Uma branch protegida so, a main; PR pequeno direto nela, com squash; um check agregado CI OK; release por tag de app
cobre: [docs/branch-strategy.md, .github/workflows/ci.yml, .github/workflows/release.yml, scripts/setup-rulesets.sh, scripts/no_commit_to_protected_branch.py]
---

# 0028 — Trunk-based com release por app

**Data:** 2026-11 (reorganização do monorepo)
**Revisa:** [0008](0008-ci-no-github-actions.md), quanto ao gatilho e aos gates do CI.

## Contexto

O guia de desenvolvimento mandava criar a branch a partir de uma `develop`, e o `ci.yml` rodava em
`pull_request` e em `push` na `main` e na `develop`. Nada no servidor impedia push direto na `main`,
o CI tinha dois jobs sem check agregado, e o passo de mypy terminava em `|| true`: existia e não
reprovava nada. Não havia modelo de PR, de issue, nem CODEOWNERS.

## Opções

1. **`main` + `develop`** — o que o guia descrevia; com mais de um app, a `develop` vira fila única
   e o release de um trava no trabalho não publicado do outro.
2. **Trunk-based com release por app (escolhida)** — `main` é a única branch protegida; PR pequeno
   direto nela; release é a tag `<app>@<versão>`.

## Decisão

Opção 2. Trabalho incompleto entra na `main` sem estar ligado no app, ou atrás de configuração. O
draft PR é o lugar de ver o CI rodar antes de pedir revisão.

## Consequências

- **Ruleset da `main`:** PR obrigatório, check agregado `CI OK`, uma aprovação de CODEOWNERS,
  aprovação descartada em push novo, quem empurrou por último não aprova, só squash, histórico
  linear, sem force-push, sem bypass. Ruleset de tags `*@*`: só o GitHub Actions cria.
- **`status: decidido-nao-executado` porque o ruleset ainda não foi aplicado no GitHub.** O script
  `scripts/setup-rulesets.sh` está no repositório; aplicar é ato de um administrador. Até lá, a
  `main` só é protegida pelo hook local (CONTRIBUTING, seção 13). Combinado em 2026-11-14: o
  ruleset completo é aplicado logo depois que esta reorganização entrar na `main`.
- **O CI roda só em `pull_request` para a `main`**, sobre o resultado do merge. Todo job está no
  `needs` do `ci-ok`, e um teste de arquitetura reprova o job que ficar de fora.
- **O mypy passa a ser gate.** Medido em 2026-11-14: zero erros em 189 arquivos.
- **Disciplina de PR pequeno:** é a proteção principal, porque um erro que passe pelo CI cai direto
  na base de todos.
- **Com dois donos, os dois precisam estar disponíveis:** ninguém aprova o próprio PR. A válvula de
  escape está descrita em [docs/branch-strategy.md](../../branch-strategy.md).
- **Commit sem co-autoria de IA e sem emoji**, com a divulgação do uso de IA no template de PR
  ([AGENTS.md](../../../AGENTS.md)).
