# Base de conhecimento

Conhecimento **destilado** do monorepo: o que uma pessoa nova (ou uma IA, no começo de cada sessão)
lê antes de re-explorar o código ou abrir a documentação longa.

Não substitui a documentação longa: resume e aponta. Quando uma nota e o código divergirem, **o
código vale**; corrija a nota e registre a data.

## O que entra aqui

| Tipo | Onde | O que é |
|---|---|---|
| Decisão (ADR) | [decisoes/](decisoes/README.md) | por que algo é como é, com as opções que foram pesadas |
| Gotcha | uma nota nesta pasta | defeito já pago: sintoma, causa, solução |
| Runbook | uma nota nesta pasta | passo a passo operacional que não cabe no CONTRIBUTING |

Antes de escrever uma nota, as três perguntas da
[regra de captura](../../AGENTS.md#a-regra-de-captura-da-kb): está fundamentada no código? a KB já
cobre? é conhecimento ou é só mapa? O número certo de notas novas é frequentemente zero.

Cada nota declara o escopo no frontmatter:

```yaml
escopo: plataforma     # vale para o monorepo inteiro
escopo: ecommerce      # só faz sentido dentro do produto da loja
```

A pergunta que decide: **um segundo produto precisaria desta nota?** Se sim, é da plataforma.

## As notas

Preencha esta tabela conforme a KB crescer. **Nota nova sem linha aqui fica invisível.**

| Nota | Escopo | Para quê | Que gasto evita |
|---|---|---|---|
| [ambiente-local-no-windows.md](ambiente-local-no-windows.md) | plataforma | os atritos de montar e usar o ambiente no Windows corporativo: política `AllSigned`, `uv` fora do PATH, o `python` do PATH que não enxerga as unidades, o `pre-commit` instalado e não reconhecido, e o GitHub CLI que o winget só instala com admin | perder uma tarde no setup, ou concluir que um comando do projeto está quebrado quando é o interpretador errado |
| [decisoes/0027](decisoes/0027-estrutura-apps-products-libs.md) | plataforma | a estrutura `apps/`, `products/`, `libs/`, os tipos de unidade e o de/para dos nomes antigos (`cores/`, `core_*`, `adapters_*`) | procurar `cores/core-catalog` citado numa ADR antiga, ou criar uma pasta `adapters/` de topo de novo |
| [decisoes/0028](decisoes/0028-trunk-based-e-release-por-app.md) | plataforma | trunk-based: branch sai da `main` e volta por PR pequeno com squash; um check agregado `CI OK`; release por tag de app | criar branch a partir de uma `develop` por hábito antigo, ou confiar num ruleset que ainda não foi aplicado |
| [decisoes/0029](decisoes/0029-workspace-uv-versao-por-unidade-e-lock-unico.md) | plataforma | workspace uv, versão por unidade, um `uv.lock`, o BOM de release; o que saiu na troca do Poetry | pinar versão exata num membro e quebrar a resolução do workspace, ou procurar o `msal` que saiu do lock |
| [decisoes/0030](decisoes/0030-tooling-proprio-e-manifesto-unit-yaml.md) | plataforma | `unit.yaml` por unidade e a CLI `uv run dev`; o que é gerado do manifesto | editar `.importlinter` ou `CODEOWNERS` à mão |
| [decisoes/0031](decisoes/0031-gates-na-maquina-pilha-em-container.md) | plataforma | os gates rodam na máquina, pelo uv; a pilha roda em container | subir container para rodar um teste unitário, ou instalar Postgres na máquina |
| [decisoes/](decisoes/README.md) | — | o índice de todas as ADRs, das decisões de produto (0003 a 0026) às de estrutura | reabrir uma discussão sem saber o que já foi pesado |

## Onde está o resto

| Quero saber… | Onde |
|---|---|
| como trabalhar aqui, do zero ao release | [CONTRIBUTING.md](../../CONTRIBUTING.md) |
| os tipos de unidade e as regras entre elas | [docs/ARQUITETURA.md](../ARQUITETURA.md) |
| o porquê de cada regra, com exemplos | [docs/onboarding/arquitetura-monorepo.md](../onboarding/arquitetura-monorepo.md) |
| branches, CI, CODEOWNERS | [docs/branch-strategy.md](../branch-strategy.md) |
| versão, release, imagem | [docs/versionamento-e-deploy.md](../versionamento-e-deploy.md) |
| a pilha local e a estratégia de testes | [docs/guides/development.md](../guides/development.md) |
| o que uma unidade faz e o que ela não faz | o `README.md` da pasta da unidade |
| os contratos da API | `products/ecommerce/contracts/api/` e [docs/api/README.md](../api/README.md) |
| o ambiente Azure | [deploy/README.md](../../deploy/README.md) |
