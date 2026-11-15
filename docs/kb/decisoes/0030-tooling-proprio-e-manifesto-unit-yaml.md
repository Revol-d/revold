---
tags: [decisao, tooling, manifesto, gates, codeowners]
status: implementado
escopo: plataforma
resumo: Um unit.yaml por unidade e uma CLI propria (uv run dev) que valida o manifesto e gera dele o .importlinter e o CODEOWNERS
cobre: [tooling, .importlinter, .github/CODEOWNERS]
---

# 0030 — Tooling próprio (`dev`) e o manifesto `unit.yaml`

**Data:** 2026-11 (reorganização do monorepo)

## Contexto

Com 27 unidades, a pergunta "quem pode importar quem" precisa de uma resposta que uma ferramenta
confira. Escrita em três lugares (um arquivo de import-linter, um CODEOWNERS e um documento), ela
diverge na primeira mudança. E o CI precisa saber o que uma branch afeta, para não rodar tudo sempre.

## Opções

1. **Manter cada arquivo à mão** — `.importlinter`, CODEOWNERS e a lista de unidades do CI
   editados separadamente; três fontes para a mesma informação.
2. **Adotar um orquestrador de monorepo pronto** — resolve afetados e cache; traz outro grafo para
   manter ao lado do workspace uv e do pnpm, e não gera os contratos de camada.
3. **Manifesto por unidade e CLI própria (escolhida)** — cada unidade declara `id`, `kind`,
   `owners` e `depends_on` num `unit.yaml`; o resto é gerado.

## Decisão

Opção 3: o pacote `revold_tooling`, em `tooling/`, exposto como `uv run dev`.

- **O `unit.yaml` é a fonte.** O schema está em `tooling/schema/unit.schema.json`.
- **`dev gen`** escreve o `.importlinter` (um contrato de dependência por unidade, e três contratos
  por unidade com camadas) e o `.github/CODEOWNERS`.
- **`dev check`** é o gate único: manifesto, gerados em dia, versões, import-linter e mypy. É o
  mesmo comando no hook e no CI.
- **`dev affected` e `dev test --affected`**: arquivos alterados, unidades, consumidores.
- **`dev new`** cria uma unidade a partir de `tooling/templates/` e desfaz tudo se algo falhar.
- **`dev bump`, `dev build`, `dev release`, `dev verify-release`**: ver a
  [0029](0029-workspace-uv-versao-por-unidade-e-lock-unico.md).

## Consequências

- **`.importlinter` e CODEOWNERS nunca se editam à mão.** O `dev check` e um teste de arquitetura
  reprovam o arquivo que não bate com o gerado.
- **Os `unit.yaml` e o próprio tooling são da plataforma** no CODEOWNERS (`platform_owners`, em
  `tooling/repo.yaml`): ninguém se põe como dono de uma unidade e aprova o próprio PR.
- **O app fica fora do import-linter**, porque existe para importar tudo. Em troca, um teste de
  arquitetura confere que ele só importa o que declara e nunca outro app.
- **O tooling é código do repositório, com testes** (`tooling/tests/`), e não entra em imagem
  nenhuma.
- **Não há modelo de site no `dev new`.** Os runtimes com modelo são `fastapi-api` e
  `celery-worker`.
- **Reavaliar** a opção 2 quando o tempo de CI ou o número de unidades tornar o cache distribuído
  mais valioso do que o custo de manter dois grafos.
