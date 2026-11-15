---
tags: [decisao, python, uv, versionamento, dependencias, release]
status: implementado
escopo: plataforma
resumo: Workspace uv no lugar do pacote Poetry unico; cada unidade com pyproject e versao proprios; um uv.lock; Python 3.12; BOM com sha256 por release de app
cobre: [pyproject.toml, uv.lock, .python-version, tooling/src/revold_tooling/release.py, tooling/src/revold_tooling/version_gate.py]
---

# 0029 — Workspace uv, versão por unidade e um lock só

**Data:** 2026-11 (reorganização do monorepo)

## Contexto

O repositório era **um** pacote Poetry, `revold 0.1.0`, que listava 21 pastas em `packages`. Uma
versão para tudo, um conjunto de dependências para tudo: a imagem do `api-gateway` instalava
langchain, celery e azure-storage-blob mesmo para rodar um comando que não usa nenhum dos três, e
não havia como dizer "esta unidade mudou, aquela não".

## Opções

1. **Manter o pacote Poetry único** — nada muda; sem fecho por app e sem versão por unidade.
2. **Poetry com um `pyproject.toml` por pasta e dependência por caminho** — dá versão por unidade;
   o Poetry não tem workspace, então são N locks, ou um lock que não enxerga os membros.
3. **Workspace uv (escolhida)** — um `pyproject.toml` por unidade, um `uv.lock` para o repositório,
   `uv sync --package <app>` instala só o fecho do app.

## Decisão

Opção 3.

- **Python 3.12** continua sendo a versão do repositório (`.python-version`, `requires-python`).
  Trocar de gerenciador e de versão de Python ao mesmo tempo misturaria duas causas de quebra.
- **Cada unidade tem a própria versão**, que sobe sozinha (`uv run dev bump`). O app só muda de
  versão no release (`uv run dev release`), depois de os testes do fecho passarem.
- **Dependência interna sem pino**; de terceiro, em faixa. Quem trava é o `uv.lock`.
- **`[tool.uv.sources]` com `workspace = true` para toda unidade**: um `revold-<nome>` nunca é
  resolvido do PyPI. O `dev check` reprova a unidade que faltar ali.
- **Um grupo de dependências só, o `dev`**, que o uv instala por padrão: `uv sync` sem argumento já
  deixa o ambiente completo.
- **O release de um app grava um BOM** em `.releases/<app>.json`: a versão e o sha256 do `src/` de
  cada unidade do fecho, e o sha256 do `uv.lock`.

## Consequências

- **As versões de terceiros não mudaram na troca.** O primeiro `uv.lock` foi resolvido com as 117
  versões do `poetry.lock` como restrição; conferido depois, nenhuma saiu diferente.
- **Quatro pacotes saíram do lock porque nenhum código os importava:** `langchain`,
  `langchain-text-splitters`, `msal` e `pydantic-settings`. O `msal` estava declarado para o login
  com o Azure AD, que ainda não tem adapter ([0003](0003-autenticacao-federada-sem-senha-propria.md));
  volta como dependência do domínio `identity` quando o adapter for escrito.
- **Dependência nova entra em dois lugares**: `depends_on` do `unit.yaml` e `dependencies` do
  `pyproject.toml`. O `dev check` reprova quando divergem.
- **O gate de versão compara conteúdo, não histórico**: o sha256 do `src/` contra o BOM do último
  release, com o fim de linha normalizado. Funciona em clone raso. Sem release gravado, não há com
  o que comparar, e o gate diz isso.
- **Os sites ficam fora do release pelo tooling**: a versão deles mora no `package.json`, e o BOM
  só cobre app Python.
- **`poetry.lock` saiu do repositório.** Os comandos `poetry run ...` dos documentos antigos viraram
  `uv run ...`.
