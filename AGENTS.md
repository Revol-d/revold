# Guia de agentes de IA — revold

Guia **canônico** para qualquer IA que trabalhe neste repositório: Claude, GPT, GitHub Copilot,
Gemini e outras. As ferramentas específicas apontam para cá: [CLAUDE.md](CLAUDE.md) e
[.github/copilot-instructions.md](.github/copilot-instructions.md).

## Regras inegociáveis de interação com o GitHub

Valem para **toda** mensagem de commit, título e descrição de PR, e comentário de PR/issue, feitos
por pessoa **ou por IA**:

1. **Nunca credite IA como co-autora.** É proibido `Co-authored-by:` de qualquer ferramenta de IA
   (Copilot, Claude, GPT e afins) e proibido apresentar geração por IA como autoria em qualquer
   commit, PR ou comentário. `Co-authored-by:` é só para pessoas reais.
2. **Nunca use emojis ou ícones** em mensagem de commit, título/descrição de PR ou comentário.
3. Isso **não** esconde o uso de IA: a **divulgação** de uso de IA (não autoria) é feita na seção
   "Uso de IA" do template de PR. Divulgar uso é diferente de creditar autoria.
4. **Nunca commite nem dê push direto na `main`.** Ela é a única branch protegida, no servidor
   (ruleset) e por hook local. **Todo** trabalho (correção, melhoria ou função nova) passa por uma
   branch nova: ela **sai da `main`** (`feat/<nome>`, `fix/<nome>`, `chore/<nome>`, `docs/<nome>`) e
   volta para a `main` **por PR**, com squash merge. Nunca trabalhe com a `main` em checkout. Ver
   [docs/branch-strategy.md](docs/branch-strategy.md) e a
   [ADR-0028](docs/kb/decisoes/0028-trunk-based-e-release-por-app.md).

## Convenções que toda IA deve seguir

- **O passo a passo completo:** [CONTRIBUTING.md](CONTRIBUTING.md). Vale para pessoa e para IA, na
  mesma ordem: issue, branch, código com teste, commit, PR em draft, revisão, squash merge.
- **Commits:** Conventional Commits, em português, no imperativo, com o `id` da unidade como escopo
  (CONTRIBUTING, seção 4.4).
- **Branches e PR:** trunk-based. **Branch nova sai da `main`** e o PR vai **para a `main`**,
  pequeno e com squash merge; para ver o CI antes de pedir revisão, abra o PR em draft.
- **PR:** preencha o template em [.github/pull_request_template.md](.github/pull_request_template.md),
  incluindo a seção "Uso de IA" quando houver uso relevante.
- **Arquitetura:** [docs/ARQUITETURA.md](docs/ARQUITETURA.md) (os tipos de unidade e as regras) e
  [docs/versionamento-e-deploy.md](docs/versionamento-e-deploy.md). Antes de criar arquivo, decida
  a unidade e a camada pela árvore da
  [aula](docs/onboarding/arquitetura-monorepo.md#44-a-árvore-de-decisão-onde-ponho-este-arquivo).
- **Gates:** rode `uv run dev check` e `uv run dev test --affected -q` antes de dizer que terminou,
  e cole a saída. "Deve passar" não é evidência.
- **Gerados:** `.importlinter` e `.github/CODEOWNERS` saem de `uv run dev gen`. Nunca edite à mão.
- **Configuração:** só o `settings.py` de um app lê variável de ambiente. Lib e produto recebem o
  valor por parâmetro.
- **Base de conhecimento:** leia [docs/kb/](docs/kb/README.md) antes de re-explorar o código. Para
  escrever nota nova, siga [A regra de captura da KB](#a-regra-de-captura-da-kb) abaixo.

## O que a IA não faz sem pedir

- **Não enfraquece barreira para fazer passar:** `# noqa`, `# type: ignore`, `# nosec`, `skip`,
  `xfail`, `continue-on-error`, `|| true`, `except Exception: pass`. Se a barreira está errada, diga
  isso e proponha a correção dela; não a contorne.
- **Não altera teste existente para ele passar.** Teste que falha depois de uma mudança de código é
  informação: primeiro confirme se o código ou o teste está errado, e diga qual no PR.
- **Não mexe em `.github/`, `.pre-commit-config.yaml`, `tooling/`, `unit.yaml` ou CODEOWNERS** fora
  de uma tarefa que peça isso.
- **Não dispara efeito fora do repositório:** push, tag, release, publicação de imagem, migração em
  banco que não seja o local, chamada a serviço pago.
- **Não sobe a versão de um app com `dev bump`.** App só sobe no `dev release` (CONTRIBUTING,
  seção 7.3).

## A regra da fonte destilada

[docs/kb/](docs/kb/README.md) é a **fonte destilada**: leia-a primeiro e só vá ao código ou aos docs
longos quando ela não responder. Ela não substitui `docs/`: resume e aponta. Quando divergirem, o
**código** vale; corrija a nota e registre a data.

## A regra de captura da KB

Ao terminar uma tarefa que produziu conhecimento não óbvio (um gotcha, uma decisão, um caminho que
custou para achar), **escreva a nota no mesmo PR**. O diff do PR é onde se revisa, como em qualquer
código.

Antes de escrever, três perguntas. Elas existem para a KB não virar depósito:

1. **Está fundamentada no código, ou só em outro documento?** Nota destilada de destilado é
   repetição que envelhece em dobro. Se o assunto não foi verificado na fonte, leia o código
   primeiro.
2. **A KB já cobre isso?** Antes de declarar buraco, abra as notas vizinhas. "A KB não fala de X" é
   uma afirmação que exige checagem, não impressão.
3. **Isso é conhecimento ou é mapa?** Documento que só precisa ser encontrado vira uma linha no
   índice [docs/kb/README.md](docs/kb/README.md), não nota. O número certo de notas novas é
   frequentemente **zero**.

Toda nota leva `cobre:` no frontmatter, com o caminho mais **estreito** que ainda a representa, e
uma linha no índice; use o modelo em
[docs/kb/templates/nota-padrao.md](docs/kb/templates/nota-padrao.md) (ou
[decisao-padrao.md](docs/kb/templates/decisao-padrao.md) para ADR).

**Nunca** ponha em nota: valor de variável de ambiente, credencial, token, connection string, ID de
recurso de nuvem, caminho absoluto de máquina ou e-mail de pessoa. Notas vão para o git e viram
contexto de IA. Cite o **nome** da variável, nunca o valor; `.env.example` é a referência, `.env`
nunca.

## Idioma

Identificadores de código (variáveis, funções, classes) em **inglês**; comentários, docstrings,
documentação e mensagens de commit em **português**.
