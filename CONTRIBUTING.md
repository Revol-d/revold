# Guia de contribuição — revold

Este é o passo a passo **completo** para trabalhar neste repositório: da máquina zerada até o
código virar release. Foi escrito para quem está começando. Se você seguir as seções na ordem, não
precisa adivinhar nada.

> **Autoridades.** Este guia é o "como fazer". O "por quê" de cada regra mora em:
> [AGENTS.md](AGENTS.md) (convenções, vale para pessoa e IA),
> [docs/branch-strategy.md](docs/branch-strategy.md) (branches, CI, CODEOWNERS),
> [docs/versionamento-e-deploy.md](docs/versionamento-e-deploy.md) (versão, release, imagem),
> [docs/ARQUITETURA.md](docs/ARQUITETURA.md) (unidades e fronteiras) e
> [docs/kb/](docs/kb/README.md) (gotchas e decisões). Quando este guia e uma delas divergirem,
> **o código vale**: avise o time e corrija o documento num PR.

## Sumário

1. [Regras inegociáveis](#1-regras-inegociáveis)
2. [Preparar a máquina (uma vez)](#2-preparar-a-máquina-uma-vez)
3. [O mapa do repositório em 2 minutos](#3-o-mapa-do-repositório-em-2-minutos)
4. [Do problema ao merge: o fluxo completo](#4-do-problema-ao-merge-o-fluxo-completo)
5. [As barreiras: o que barra você, onde e como resolver](#5-as-barreiras-o-que-barra-você-onde-e-como-resolver)
6. [CODEOWNERS: quem pode aprovar o quê](#6-codeowners-quem-pode-aprovar-o-quê)
7. [Versionamento](#7-versionamento)
8. [Análise para deploy e release](#8-análise-para-deploy-e-release)
9. [Operação: a pilha local e o ambiente Azure](#9-operação-a-pilha-local-e-o-ambiente-azure)
10. [Testes](#10-testes)
11. [Padrões de código](#11-padrões-de-código)
12. [Erros comuns e como sair deles](#12-erros-comuns-e-como-sair-deles)
13. [Pontos em aberto (o que ainda não protege)](#13-pontos-em-aberto-o-que-ainda-não-protege)
14. [Ajuda, segurança e base de conhecimento](#14-ajuda-segurança-e-base-de-conhecimento)

---

## 1. Regras inegociáveis

Valem para **toda** mensagem de commit, título e descrição de PR, issue e comentário, feitos por
pessoa **ou por IA**:

1. **Nunca commite nem dê push direto na `main`.** Todo trabalho sai de uma branch nova a partir da
   `origin/main` e volta por PR, com squash merge.
2. **Nunca credite IA como co-autora.** Proibido `Co-authored-by:` de Copilot, Claude, GPT e afins.
   `Co-authored-by:` é só para pessoas. Se a sua ferramenta de IA acrescentar essa linha sozinha,
   apague antes de commitar.
3. **Divulgar uso de IA é obrigatório; creditar autoria é proibido.** A divulgação vai na seção
   "Uso de IA" do template de PR.
4. **Sem emojis ou ícones** em commit, PR, issue ou comentário.
5. **Idioma:** identificadores de código (variáveis, funções, classes) em **inglês**; comentários,
   docstrings, documentação e mensagens de commit em **português**.
6. **Nunca pule hook** com `git commit --no-verify` ou `git push --no-verify`. Se um hook travar por
   algo que não é seu, peça ajuda (seção 14). O CI roda as mesmas checagens e reprova do mesmo jeito.
7. **Nunca commite segredo** (senha, token, connection string, chave) nem **valor** de variável de
   ambiente, caminho absoluto da sua máquina ou e-mail de pessoa. Cite o **nome** da variável. O
   `.env` nunca vai para o git. Vazou? Siga o [SECURITY.md](SECURITY.md), não abra issue.
8. **Nome de cliente não entra em `libs/`.** Uma lib existe para ser reusada por outro produto, e
   nome de cliente na assinatura, no nome de arquivo ou numa variável de ambiente nova é o oposto
   disso. O que ainda existe com o nome do cliente piloto, e o plano para tirar, está na seção
   13, item 11. Até lá, não acrescente mais.
9. **Não rode teste contra serviço pago nem contra banco que não seja de teste.** Os testes
   marcados `integration` **gravam** no banco de `DATABASE_URL`/`TEST_DATABASE_URL`. O eval
   `test_llm_judge` chama um LLM de verdade quando `LLM_PROVIDER=azure-openai` tem credencial
   (seção 10).
10. **Quem abre o PR responde por cada linha**, inclusive pelas que a IA escreveu. Se você não
    consegue explicar um trecho, ele não entra (seção 4.9).

---

## 2. Preparar a máquina (uma vez)

Os comandos abaixo são para o **PowerShell**, no Windows. Se algo travar, leia
[docs/kb/ambiente-local-no-windows.md](docs/kb/ambiente-local-no-windows.md): ela cobre a política
`AllSigned`, o `uv` fora do PATH e os outros atritos conhecidos.

### 2.1 Ferramentas

| Ferramenta | Para quê | Como instalar | Como conferir |
|---|---|---|---|
| Git | versionamento | `winget install --id Git.Git -e` | `git --version` |
| uv | Python, dependências, comandos do projeto | `winget install --id=astral-sh.uv -e` | `uv --version` |
| Python 3.12 | versão oficial do repositório ([ADR-0029](docs/kb/decisoes/0029-workspace-uv-versao-por-unidade-e-lock-unico.md)) | `uv python install 3.12` | `uv run python --version` |
| pre-commit | os hooks locais (seção 5) | `uv tool install pre-commit` e depois `uv tool update-shell` (põe `%USERPROFILE%\.local\bin` no PATH) | `pre-commit --version`, num terminal **novo** |
| GitHub CLI | issue, branch ligada a issue, PR | **sem admin**: o zip da seção 2.1.1 (o `winget` pede admin e falha com `1602`); depois `gh auth login` | `gh auth status`, num terminal **novo** |
| Docker Desktop | a pilha local: Azure SQL, Redis, API, worker, sites (seção 9) | instalador do site da Docker | `docker --version` |
| Node 20+ e pnpm 9 | **só** se for mexer nos sites ou em `libs/web/` | `winget install OpenJS.NodeJS.LTS` e depois `corepack enable` | `pnpm --version` |

Depois de instalar, **feche e reabra o VS Code inteiro**: ele herda o PATH do momento em que abriu.

#### 2.1.1 GitHub CLI sem administrador

O `winget install --id GitHub.cli` usa o instalador MSI, que instala para todos os usuários e por
isso pede administrador. Sem admin ele termina com `Installer failed with exit code: 1602`. O
caminho que funciona é a versão portátil, no seu perfil, no PowerShell comum:

```powershell
$versao = "2.103.3"   # a mais nova em https://github.com/cli/cli/releases
$destino = "$env:LOCALAPPDATA\Programs\gh"
$zip = "$env:TEMP\gh.zip"
Invoke-WebRequest "https://github.com/cli/cli/releases/download/v$versao/gh_${versao}_windows_amd64.zip" -OutFile $zip
Expand-Archive $zip -DestinationPath $destino -Force
Remove-Item $zip

$bin = "$destino\bin"
$path = [Environment]::GetEnvironmentVariable("Path", "User")
if (($path -split ';') -notcontains $bin) {
    [Environment]::SetEnvironmentVariable("Path", "$path;$bin", "User")
}
```

Feche e reabra o terminal (ou o VS Code inteiro) e rode:

```powershell
gh --version
gh auth login     # GitHub.com -> HTTPS -> Login with a web browser
```

Sem o `gh`, todo o fluxo da seção 4 também funciona pelo site do GitHub.

No VS Code, desligue a ativação automática do venv (`settings.json` do usuário). Ela gera um aviso
de segurança a cada terminal, e o projeto não precisa dela, porque tudo roda por `uv run`:

```json
"python.terminal.activateEnvironment": false
```

### 2.2 Clonar e instalar

```powershell
git clone https://github.com/SamuelSMatos/revold.git
cd revold

uv sync
```

O `uv sync` instala todas as unidades do monorepo em modo editável e o grupo `dev` (pytest, ruff,
mypy), que é o padrão do uv. Não há grupo para lembrar.

Se for mexer nos sites:

```powershell
pnpm install
```

### 2.3 Ligar os hooks (o passo que todo mundo esquece)

Sem isto, nenhuma barreira local roda e você só descobre o erro no CI, depois do push:

```powershell
pre-commit install
pre-commit install --hook-type pre-push
```

Para conferir, a pasta `.git/hooks/` precisa ter os arquivos `pre-commit` e `pre-push` (sem
`.sample` no nome).

### 2.4 Variáveis de ambiente

```powershell
Copy-Item .env.example .env
```

O `.env.example` já vem com os valores de desenvolvimento: todo provedor externo (login, LLM,
pagamento, notificação) aponta para o adapter de desenvolvimento, que não usa credencial. Só troque
o que a sua tarefa pede. O `.env` é lido pelo Docker Compose; os testes e os gates rodados na
máquina não precisam dele.

### 2.5 Conferir que está tudo de pé

```powershell
uv run dev check
uv run dev test -q
```

Os dois têm que terminar sem falha. O primeiro confere manifestos, fronteiras e tipos; o segundo
roda a suíte inteira (um a dois minutos). Pulados (`skipped`) são normais: são os testes que exigem
Azure SQL, Redis, Azurite ou LLM de verdade (seção 10).

---

## 3. O mapa do repositório em 2 minutos

O repositório é um **monolito modular**: várias unidades Python (e três TypeScript) num só lugar,
cada uma com fronteira travada por gate. A aula completa, em texto:
[docs/onboarding/arquitetura-monorepo.md](docs/onboarding/arquitetura-monorepo.md).

| Pasta | O que tem | Exemplo |
|---|---|---|
| `apps/` | os **apps**: o que roda de verdade. Só o app lê ambiente e monta adapters | `apps/ecommerce/api-gateway/` |
| `products/` | a regra de um produto: o que cruza dois ou mais domínios | `products/ecommerce/` |
| `libs/` | bibliotecas compartilhadas: `platform`, `integrations`, `domains`, `web` | `libs/domains/catalog/` |
| `tooling/` | a ferramenta `uv run dev ...` | |
| `deploy/` | o que leva um app ao ambiente: Terraform (Azure) e a observabilidade local | `deploy/terraform/` |
| `.releases/` | o BOM versionado de cada release de app | |
| `tests/` | a suíte central (arquitetura) e o apoio de teste compartilhado | `tests/architecture/` |
| `docs/` | arquitetura, decisões (ADR), base de conhecimento | `docs/kb/decisoes/` |

Cada unidade tem um **`unit.yaml`**: o manifesto com `id`, `kind`, `owners` e `depends_on`. É dele
que saem as fronteiras, o CODEOWNERS e o fecho de cada release. **Uma unidade só pode importar o
que declara em `depends_on`.**

Onde pôr um arquivo novo? Use a árvore de decisão da seção 4.4 da
[aula de arquitetura](docs/onboarding/arquitetura-monorepo.md#44-a-árvore-de-decisão-onde-ponho-este-arquivo).

---

## 4. Do problema ao merge: o fluxo completo

```text
1. Issue        o que fazer, em qual unidade, com critério de aceite
2. Branch       sai da origin/main, com o número da issue no nome
3. Código       pequeno, com teste, dentro da unidade certa
4. Commit       Conventional Commits, hooks de pre-commit rodam
5. Push         hooks de pre-push rodam (mypy, testes)
6. PR draft     o CI roda; ninguém é chamado para revisar ainda
7. Ready        CI verde -> "Ready for review"; o CODEOWNERS chama o revisor
8. Revisão      ajustes em commits novos na mesma branch
9. Squash merge a branch some, a issue fecha sozinha
10. Release     só quando o código precisa virar imagem publicada (seção 8)
```

### 4.0 As branches e onde o CI roda

**Só existe uma branch permanente: a `main`.** Todo o resto é branch de trabalho, de vida curta, que
nasce da `origin/main` e morre no squash merge. **Não existe `develop`**
([ADR-0028](docs/kb/decisoes/0028-trunk-based-e-release-por-app.md)).

| Branch | Quem cria | Vida | Para onde vai |
|---|---|---|---|
| `main` | já existe | permanente, protegida | ninguém empurra nela |
| `feat/<issue>-<resumo>`, `fix/...`, `chore/...`, `docs/...` | você | dias, não semanas | PR para a `main` |
| `chore/release-<app>` | quem faz o release | horas | PR para a `main` (seção 8) |

**Onde o CI roda:**

- **Em todo PR para a `main`, inclusive em draft**, a cada push na branch do PR. É assim que você
  testa: abra o PR em draft logo no primeiro push.
- **Na aba Actions -> CI -> Run workflow**, numa branch sem PR, se precisar.
- **Nunca em push sem PR.** Branch empurrada sem PR não roda nada.
- O `release.yml` roda sozinho quando um PR de release entra na `main`.

**Branch longa é o risco principal do modelo.** Sem `develop` no meio, o PR vai direto para a base
de todo mundo. Se a sua branch passou de uma semana ou de umas 400 linhas, quebre em PRs menores.

### 4.1 Abrir a issue

**Todo trabalho começa numa issue**, inclusive correção pequena: é ela que diz o que é "pronto".

1. No GitHub, aba **Issues** -> **New issue**. Escolha o modelo:
   - **Tarefa**: feature, refatoração, documentação, chore;
   - **Relato de bug**: algo que funcionava e quebrou;
   - **Dúvida**: não abra issue, siga o [SUPPORT.md](SUPPORT.md);
   - **Segurança ou segredo vazado**: **nunca** issue, siga o [SECURITY.md](SECURITY.md).
2. Preencha **todos** os campos obrigatórios:
   - **Unidade**: o `id` do `unit.yaml` que a tarefa altera. Em dúvida, marque "nao sei" e pergunte
     antes de começar.
   - **Tipo**: `feat`, `fix`, `chore` ou `docs`.
   - **Objetivo**, **Escopo** (dentro e fora) e **Critérios de aceite**: frases que alguém consegue
     conferir com sim ou não.
3. **Título** curto e no imperativo, sem prefixo: "Permitir cupom de desconto no carrinho", não
   "feat: cupom".
4. **Labels**: o modelo de Tarefa **não** aplica label sozinho. Aplique na barra lateral:
   - `tipo:feat`, `tipo:fix`, `tipo:chore` ou `tipo:docs`;
   - `unidade:<id>` (a mesma do campo Unidade);
   - `produto:ecommerce`, se for do produto da loja.
5. **Regra de tamanho: uma issue, um PR, uma unidade.** Se a tarefa mexe em duas unidades (um
   domínio e o app, por exemplo), quebre em duas issues. A exceção é quando a mudança precisa entrar
   junta para nada quebrar no meio; nesse caso, diga isso na issue.
6. **Pronta para começar** quando: objetivo claro, unidade definida, critério de aceite conferível e
   ninguém mais trabalhando nela. Atribua a issue a você (**Assignees**) antes de criar a branch.

Pela linha de comando, o mesmo:

```powershell
gh issue create --title "Permitir cupom de desconto no carrinho" --label "tipo:feat,unidade:cart,produto:ecommerce"
```

(o `gh` abre o editor para o corpo; copie os campos do modelo de Tarefa.)

### 4.2 Criar a branch

A branch **sempre** sai da `origin/main` (a do servidor), nunca da sua `main` local, que pode estar
velha. Nome: `<tipo>/<numero-da-issue>-<resumo-curto>`.

O jeito recomendado, que já liga a branch à issue:

```powershell
gh issue develop 123 --name feat/123-cupom-no-carrinho --base main --checkout
```

Sem o `gh`:

```powershell
git fetch origin
git switch -c feat/123-cupom-no-carrinho origin/main
```

Tipos de branch: `feat/`, `fix/`, `chore/`, `docs/`. Não trabalhe com a `main` em checkout; o hook
`no-commit-to-protected-branch` recusa o commit se você tentar.

### 4.3 Desenvolver

- **Fique dentro da unidade da issue.** Precisou mexer em outra? Pare e pergunte: provavelmente é
  outra issue.
- **Respeite as camadas** (seção 11). O gate reprova import proibido, mas é mais barato acertar de
  primeira.
- **Escreva o teste junto.** Correção de bug começa por um teste que falha mostrando o bug.
- **PR pequeno.** O ideal é que alguém revise em 20 minutos. Trabalho grande entra em partes,
  desligado no app ou atrás de configuração, até ficar completo.
- **Mudou o `src/` de uma lib, do produto ou de um app?** Leia a seção 7 antes de abrir o PR: talvez
  a versão precise subir.
- **Mudou tabela?** A migração Alembic vai no mesmo PR, em `products/ecommerce/migrations/`,
  gerada pelo `--autogenerate` e revisada (seção 9.3).

### 4.4 Commitar

Formato Conventional Commits, em português, no imperativo. O **escopo** é o `id` da unidade (ou
`ci`, `docs`, `deploy`, `tooling`):

```text
feat(cart): aceita cupom de desconto no total
fix(mercado-pago): repete a consulta de status quando a API devolve 502
test(inventory): cobre a reserva concorrente do mesmo SKU
docs: explica o fluxo de issue no CONTRIBUTING
chore(release): api-gateway 0.2.0
```

| Tipo | Quando |
|---|---|
| `feat` | comportamento novo |
| `fix` | corrige comportamento errado |
| `refactor` | muda a estrutura sem mudar o comportamento |
| `test` | só testes |
| `docs` | só documentação |
| `chore` | versão, dependência, ferramental |
| `ci` | workflows do GitHub |

Corpo do commit: **o porquê**, não o que (o diff já mostra o que). Nada de linha de IA no rodapé.

```powershell
git add <arquivos>
git commit
```

Os hooks de pre-commit rodam agora (seção 5.1). Se um deles **corrigir** um arquivo (espaço no fim
da linha, quebra de linha), o commit falha de propósito: confira o que mudou, rode `git add` de novo
e commite outra vez.

### 4.5 Validar antes do push

```powershell
uv run dev affected          # o que a sua branch afeta
uv run dev test --affected -q
uv run dev check             # manifesto, versões, fronteiras e mypy
uv run ruff check .
```

### 4.6 Push e PR em draft

```powershell
git push -u origin feat/123-cupom-no-carrinho
```

**O que acontece ao dar `git push`:** antes de enviar qualquer coisa ao GitHub, o Git roda os hooks
de pre-push **na sua máquina** (mypy e os testes das unidades afetadas; leva um ou dois minutos, e
o terminal parece parado enquanto isso).

```text
git push
   |
   v
hooks de pre-push na sua máquina
   |-- algum falhou?   -> o push é CANCELADO, nada vai para o GitHub.
   |                      Corrija, commite e rode o git push de novo.
   |-- todos passaram? -> os commits são enviados ao GitHub.
```

O que roda em cada hook está na seção 5.2. Eles só existem se você fez a seção 2.3; sem ela, o push
sai sem checagem e o erro só aparece no CI.

**Depois do push, abra o PR.** O push só manda o código; o CI do GitHub começa quando o PR existe:

```powershell
gh pr create --base main --draft --fill
```

Ou pelo site: **Compare & pull request** -> setinha do botão -> **Create draft pull request**.

No PR:

1. **Título** em Conventional Commits, porque ele vira a mensagem do commit na `main`:
   `feat(cart): aceita cupom de desconto no total`.
2. **Descrição**: preencha o template. As seções que importam de verdade:
   - **Resumo** e **Escopo** (dentro e fora);
   - **Uso de IA**: marque e responda as perguntas por escrito, se houve (seção 4.9);
   - **Testes executados**, com o comando que você rodou;
   - **Build, deploy e rollback**, se a mudança vai virar release (seção 8);
   - a linha `Closes #123`, que fecha a issue no merge.
3. Espere o **`CI OK`** ficar verde. O draft é a pista livre: empurre quantas vezes precisar.

### 4.7 Pedir revisão e responder

1. CI verde -> **autorrevisão** -> **Ready for review**. Na autorrevisão, leia o diff inteiro na aba
   **Files changed** do GitHub (não no editor) e comente você mesmo os trechos que acharia estranhos
   num PR alheio. Depois disso o GitHub chama os donos do CODEOWNERS sozinho (seção 6).
2. O revisor comenta. Responda **com commits novos na mesma branch**, nunca com branch nova.
3. **Todo push novo derruba a aprovação anterior** (regra do ruleset), e quem empurrou por último
   não pode aprovar. Depois de ajustar, peça a revisão de novo (botão de reciclar ao lado do nome do
   revisor).
4. A `main` andou e deu conflito? Atualize a **sua** branch:

   ```powershell
   git fetch origin
   git rebase origin/main
   # resolva os conflitos, git add, git rebase --continue
   git push --force-with-lease
   ```

   `--force-with-lease` só na **sua** branch de trabalho. Na `main` o servidor recusa qualquer
   force-push.

### 4.8 Merge e depois

- O merge é **só squash**. Quem clica é o autor, depois da aprovação e do `CI OK` verde.
- A branch remota é apagada sozinha e a issue fecha pelo `Closes #123`.
- Na sua máquina: `git fetch --prune` e apague a branch local (`git branch -d <nome>`).
- O merge **não** publica nada. Publicar é release (seção 8).

### 4.9 Revisão de código gerado por IA

O checklist do template de PR é o resumo do processo inteiro e continua valendo. Esta seção explica
o que está por trás dos itens de IA: os erros que a IA comete com mais frequência e que o CI **não**
pega. Vale para o autor (na autorrevisão) e para o revisor. Os casos citados são deste repositório.

**O que não gastar tempo revisando:** lint, tipos, fronteiras entre unidades, testes rodando e
bandit. Os hooks e o `CI OK` já cobrem (seção 5).

**O que revisar, em ordem de prioridade:**

1. **Teste que não testa nada.** É o mais perigoso, porque o CI fica verde. Desconfie de:
   - teste **existente** alterado no mesmo PR que o código (a IA tende a ajustar o teste até ele
     passar, em vez de corrigir o código);
   - `assert` enfraquecido ou trocado por "não deu erro";
   - `skip`, `xfail` ou mudança de marcador sem explicação;
   - mock que só confere a si mesmo (o teste chama o mock e verifica que o mock foi chamado).

   Caso real: os testes de integração do repositório do catálogo pulavam sozinhos sem Postgres, o
   CI não tinha Postgres, e a suíte verde escondia que eles nunca rodavam. Só apareceu quando o
   service do Postgres entrou no workflow. Teste de mesa: quebre o código de propósito e rode o
   teste. Ele precisa falhar.
2. **Coisa plausível que não existe ou não funciona no ambiente real.** Função, parâmetro, flag ou
   comportamento que parece certo e não é. Dois casos reais: a pasta de mídia tinha `/app/media`
   como padrão, que só existe dentro do container, e fora dele a API nem importava
   (`PermissionError`, [ADR-0021](docs/kb/decisoes/0021-reproducao-local-do-ci-e-correcao-de-falhas-so-reproduziveis-no-runner.md));
   e o `docker compose run` reaproveitou uma imagem montada antes de um módulo existir, e o seed
   falhou com `No module named`. Tudo que roda fora do pytest (container, Mercado Pago, WhatsApp,
   SMTP, Azure) precisa de evidência de execução real ou de link para a documentação oficial.
3. **Barreira enfraquecida.** A IA remove obstáculos para "fazer funcionar". Cada item abaixo exige
   justificativa escrita no PR:
   - `# noqa`, `# type: ignore`, `# nosec`;
   - `except Exception:` amplo, `pass` em bloco de erro, fallback silencioso;
   - validação removida;
   - `|| true` ou `continue-on-error` num passo de CI (o mypy rodou assim no CI antigo: o passo
     existia e não reprovava nada);
   - mudança em `.github/`, `.pre-commit-config.yaml`, `CODEOWNERS`, `unit.yaml` ou `tooling/`.

   Caso real de fallback silencioso: o `docker-compose.yml` fixava `NOTIFICATION_PROVIDER=logging`,
   e qualquer valor posto no `.env` era ignorado sem aviso. Ninguém percebeu porque o canal de
   e-mail nunca tinha sido exercitado pela pilha de verdade.
4. **Atalho no fluxo.** A IA conhece o caminho curto e usa: versão de app subida com `dev bump` em
   vez de `dev release` (seção 7.3), `.importlinter` editado à mão em vez de gerado, dependência
   posta só no `pyproject.toml` e esquecida no `unit.yaml`. Pergunta do revisor: "isso seguiu este
   CONTRIBUTING ou deu a volta?"
5. **Efeito colateral fora do repositório.** Criar cobrança no gateway de pagamento, mandar e-mail
   ou WhatsApp, apagar dado, rodar migração, chamar API com credencial, logar dado pessoal ou
   segredo. Para a IA é uma linha qualquer; para o negócio é a mais cara. Leia cada uma dessas
   chamadas com calma.
6. **Afirmação sem prova.** Na descrição do PR, na documentação ou em comentário: "testes
   passando", "o gate protege", "validado em produção". Toda afirmação de que algo funciona vem com
   o comando rodado e a saída colada. O que não foi verificado se diz que não foi, como o README do
   Terraform faz ("ainda não foi aplicado nem validado") e os adapters em sandbox fazem ("valida o
   formato documentado, não o comportamento real do serviço").
7. **Escopo e reinvenção.** Arquivo que a issue não pede, refatoração desnecessária, helper novo
   quando já existe um parecido, dependência nova.

**Tamanho do PR (recomendação, não bloqueio):** mire em até **cerca de 400 linhas** alteradas de
código escrito (à mão ou por IA). Arquivo gerado (`uv.lock`, `pnpm-lock.yaml`, `CODEOWNERS`,
`.importlinter`) não conta. Acima disso, prefira dividir em PRs menores; se não fizer sentido
dividir, explique na descrição por quê. Diff grande gerado por IA não se revisa de verdade, só se
folheia.

**Revisão por IA complementa, não substitui.** Rodar uma revisão automática antes de abrir o PR
ajuda a pegar erro bobo, mas a aprovação do CODEOWNER é humana e obrigatória. O revisor pode pedir
"rode isto e cole a saída" em qualquer ponto, e "foi a IA que escreveu" não é resposta para "por que
isso está aqui?".

---

## 5. As barreiras: o que barra você, onde e como resolver

São cinco camadas, uma depois da outra:

```text
pre-commit (cada commit)  ->  pre-push (cada push)  ->  CI "CI OK" (cada PR)
      ->  ruleset do GitHub (merge na main)  ->  release.yml (release)
```

### 5.1 Hooks de pre-commit (no `git commit`)

| Hook | O que barra | Como resolver |
|---|---|---|
| `no-commit-to-protected-branch` | commit com a `main` em checkout | `git switch -c feat/...` e commite lá |
| `trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending` | espaço no fim, falta de quebra de linha, CRLF | já corrigem sozinhos: `git add` e commite de novo |
| `check-yaml`, `check-json`, `check-toml` | YAML, JSON ou TOML quebrado | corrija a sintaxe |
| `check-added-large-files` | arquivo acima de 500 KB | não versione binário grande (imagem pesada, dump) |
| `check-merge-conflict`, `check-case-conflict` | marcador de conflito esquecido, nomes que só diferem em maiúscula | resolva o conflito / renomeie |
| `ruff-check` | erro de lint | `uv run ruff check . --fix` resolve boa parte; o resto, à mão |
| `dev-check` | `unit.yaml` inválido, `.importlinter`/CODEOWNERS desatualizados, import proibido entre unidades ou camadas, **versão que não subiu** | a mensagem traz o comando (`uv run dev gen` ou `uv run dev bump <unidade> patch`) |

### 5.2 Hooks de pre-push (no `git push`)

| Hook | O que barra |
|---|---|
| `no-commit-to-protected-branch` | push com a `main` em checkout |
| `mypy` (`uv run dev check`) | erro de tipo, além de tudo o que o `dev-check` barra |
| `pytest-affected` (`uv run dev test --affected`) | teste quebrado nas unidades que a branch afeta |

### 5.3 CI (no PR): um check só, o `CI OK`

O `.github/workflows/ci.yml` tem vários jobs, e o ruleset exige **um**: o `CI OK`, que só fica verde
se todos os outros passarem.

| Job | O que confere |
|---|---|
| Lint (ruff) | `uv run ruff check .` |
| Hooks do pre-commit | os mesmos hooks de commit da seção 5.1, em todos os arquivos (o ruff e o `dev check` têm job próprio) |
| Manifesto, fronteiras e tipos | `uv run dev check`: manifesto, gerados em dia, versões, import-linter e mypy |
| Unidades afetadas | quais unidades a branch toca, mais os consumidores delas |
| Testes (Python) | os testes das unidades afetadas, com um Azure SQL de verdade e as migrações aplicadas |
| Frontend | `pnpm lint` e `pnpm build`, se a branch tocou em unidade TypeScript |
| Imagem `<site>` | o `docker build` da imagem de cada site, se a branch tocou em unidade TypeScript |
| E2E (Playwright) | sobe banco, fila, API e loja e roda a prova de cliente (carrinho, checkout, busca), se a branch afetou a loja ou a API |
| Segurança | `bandit` (reprova), busca das credenciais do projeto no código (reprova), `pip-audit` (informativo) |
| Imagem `<app>` | o BOM do fecho, o `docker build` da imagem de cada app Python e o import do app dentro dela |

> **Tudo o que o hook de commit confere, o CI confere também**, com a mesma versão: os hooks de
> arquivo no job "Hooks do pre-commit", e o `ruff` e o `dev check` nos jobs deles. Quem não
> instalou os hooks descobre o erro no PR, e não na `main`. O contrário não vale: o `bandit`, o
> `pip-audit`, o frontend, as imagens e o E2E rodam **só** no CI.
> Os testes de integração rodam **só** onde há Azure SQL: no CI, ou na sua máquina com a pilha de pé
> (seção 10). Se o CI reprovar algo que o hook deixou passar, a correção é a mesma: rode a
> ferramenta que o CI aponta.

### 5.4 Ruleset do GitHub (no merge)

Configurado por `scripts/setup-rulesets.sh` (detalhes em
[docs/branch-strategy.md](docs/branch-strategy.md#checklist-para-repositório-novo)). Na `main`:

- push direto, force-push e deleção: **recusados** no servidor;
- merge só por **PR**, só **squash**, histórico linear;
- exige o **`CI OK`** verde;
- exige **1 aprovação de CODEOWNER** (seção 6);
- **push novo derruba aprovação** anterior;
- **quem fez o último push não pode aprovar**;
- **ninguém** na lista de bypass, nem administrador.

Nas tags `*@*` (release): só o GitHub Actions cria, move ou apaga.

### 5.5 Release (na publicação)

- O `release.yml` confere o BOM aprovado no PR contra o código que entrou na `main` e **para** se
  alguma unidade tiver outra versão ou outro conteúdo, ou se o `uv.lock` for outro.
- A tag `<app>@<versão>` só nasce depois dessa conferência, criada pelo próprio workflow.

---

## 6. CODEOWNERS: quem pode aprovar o quê

### 6.1 Como funciona

- O arquivo [.github/CODEOWNERS](.github/CODEOWNERS) diz quem é dono de cada pasta. Ele é **gerado**
  por `uv run dev gen` a partir do campo `owners` de cada `unit.yaml` e do
  [tooling/repo.yaml](tooling/repo.yaml). **Nunca edite à mão**: o `dev check` reprova o
  CODEOWNERS que não bate com o gerado.
- Quando um PR toca uma pasta, o GitHub pede a revisão dos donos dela. O ruleset exige a aprovação
  de **pelo menos um** dono.
- **Os próprios `unit.yaml` e o ferramental são da plataforma** (`platform_owners` no
  `tooling/repo.yaml`): `.github/`, `tooling/`, `deploy/`, `scripts/`, `.releases/`,
  `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.importlinter`, `docker-compose.yml` e o
  `Makefile`. Isso impede alguém de se pôr como dono de uma unidade e aprovar o próprio PR
  ([ADR-0030](docs/kb/decisoes/0030-tooling-proprio-e-manifesto-unit-yaml.md)).

### 6.2 O que isso significa para quem não é dono

- **Você pode** criar branch, commitar, abrir PR e mexer em qualquer arquivo **na sua branch**. O
  gate não impede editar; ele impede **entrar na `main`** sem aprovação.
- **Você não consegue** mergear sem a aprovação de um dono da pasta que tocou, nem com o CI
  vermelho, nem por push direto.
- **Ninguém aprova o próprio PR** (regra do GitHub), e quem empurrou o último commit também não
  aprova o PR em que empurrou.

### 6.3 Como está hoje

Os dois donos (`@SamuelSMatos` e `@dmourans`) são donos de **tudo**. Na prática, o PR de um
precisa da aprovação do outro. Quando o time crescer, cada unidade pode ganhar donos próprios:

1. abra uma issue `chore` para a plataforma;
2. no PR, edite o `owners` do `unit.yaml` da unidade e rode `uv run dev gen`;
3. commite o `unit.yaml` **e** o CODEOWNERS regenerado. Como o `unit.yaml` é da plataforma, um dos
   donos da plataforma precisa aprovar.

Dono novo precisa ser **colaborador** do repositório. Usuário com nome errado no `owners` é
ignorado pelo GitHub **sem aviso**. Depois de trocar, abra um PR de teste e confira se o GitHub
chamou o dono certo.

---

## 7. Versionamento

### 7.1 Cada unidade tem a sua versão

A versão de cada lib, do produto e de cada app está no `pyproject.toml` dela. Mexer numa unidade
sobe **só a versão dela**
([ADR-0029](docs/kb/decisoes/0029-workspace-uv-versao-por-unidade-e-lock-unico.md)).

```powershell
uv run dev version                     # versão de cada unidade
uv run dev bump catalog patch          # 0.1.0 -> 0.1.1, só ela (e atualiza o uv.lock)
```

### 7.2 Quando subir a versão (regra do time)

Todas as unidades estão em `0.x`. A regra:

| Parte | Quando | Exemplo |
|---|---|---|
| `patch` (0.2.0 -> 0.2.1) | correção ou ajuste interno, sem mudar o que outras unidades importam | corrigir o cálculo do total do carrinho |
| `minor` (0.2.0 -> 0.3.0) | função, classe ou adapter novo, **ou** mudança no que outras unidades importam (em `0.x`, quebra também é `minor`) | adapter novo de pagamento; parâmetro novo obrigatório |
| `major` (0.x -> 1.0.0) | só por decisão registrada em ADR | estabilizar a API pública |

**Quando é obrigatório:** sempre que o `src/` de uma unidade do fecho de um app mudou desde o
último release daquele app. Teste, README e `unit.yaml` não contam: não mudam o que a imagem
instala.

**Antes do primeiro release de um app, a regra ainda não vale para as unidades dele.** Nada foi
publicado, então não existe número para proteger: subir a versão é opcional. A obrigação começa
sozinha no primeiro `uv run dev release` do app, que é quando o gate ganha com o que comparar
(seção 13, item 1).

**Por que é obrigatório:** o número é como se sabe o que está publicado. Mesmo número com outro
conteúdo é uma imagem que diz ser uma coisa e é outra, e o `dev check` reprova isso.

**Em que PR:** o bump vai **no mesmo PR** da mudança de código, com o `uv.lock` que o `dev bump`
atualizou.

### 7.3 O app só sobe no release

A versão de um **app** (`api-gateway`, `event-worker`, `catalog-indexer`) **não** se sobe com
`dev bump`. Ela sobe no `uv run dev release`, que primeiro prova que o conjunto inteiro funciona
(seção 8).

### 7.4 Dependências

- Entre unidades: **sem pino** (`"revold-catalog"`, nunca `"revold-catalog==0.2.0"`), e sempre nos
  **dois** lugares: `depends_on` do `unit.yaml` e `dependencies` do `pyproject.toml`. O `dev check`
  reprova quando os dois divergem.
- De terceiros: em **faixa** (`"httpx>=0.27.2,<0.28"`). A trava de verdade é o `uv.lock`, que é um
  só para o repositório inteiro.
- Dependência nova: `uv add --package <distribuição> "<pacote>>=X,<Y"`. Commite o `pyproject.toml`
  e o `uv.lock` juntos e justifique no PR.
- Um app só importa o que declara: o ambiente de desenvolvimento tem todas as unidades instaladas,
  mas a imagem do app só leva o fecho declarado. Um teste de arquitetura reprova o import a mais.

---

## 8. Análise para deploy e release

Merge na `main` não publica nada. Para o código virar imagem com número, alguém faz um **release**.
Esta seção é o roteiro de quem faz.

### 8.1 Precisa de release?

Sim, se o que entrou desde o último release do app mudou **qualquer** destes:

- o `src/` de uma unidade do fecho do app (veja o `depends_on` do `unit.yaml` do app, ou
  `uv run dev release <app> patch --dry-run`);
- o `Dockerfile` do app;
- uma migração em `products/ecommerce/migrations/`;
- o `uv.lock` (dependência de terceiro que a imagem instala).

Mudança só em teste, docs ou CI não precisa de release.

### 8.2 Antes do release: as perguntas da análise

Responda por escrito na seção "Build, deploy e rollback" do PR de release:

| Pergunta | Se a resposta for sim |
|---|---|
| Muda o schema do banco (tabela, coluna, índice)? | a migração Alembic está no fecho, tem `downgrade` e roda **antes** da imagem nova; escreva a ordem |
| Muda variável de ambiente ou segredo? | atualize o `.env.example` e o `settings.py` do app, e avise quem opera o ambiente |
| Muda o contrato da API (`products/ecommerce/contracts/api/`)? | os sites que consomem o endpoint entram no mesmo ciclo, ou a mudança é compatível |
| Muda o nome ou o formato de um evento? | produtor (api-gateway) e consumidor (event-worker) saem juntos |
| Muda provedor externo (pagamento, e-mail, WhatsApp, LLM)? | exercite no adapter de desenvolvimento antes; diga o que **não** foi validado contra o serviço real |
| Dá para voltar? | escreva o plano de volta: qual tag anterior, e o que fazer com a migração |

### 8.3 O release, passo a passo

```powershell
git fetch origin
git switch -c chore/release-api-gateway origin/main

uv run dev check                                  # tudo em dia? (versões, fronteiras, mypy)
uv run dev release api-gateway patch --dry-run    # mostra o fecho e o que mudou desde o último release
```

Leia a saída do dry-run: a lista de unidades com versão nova tem que bater com o que entrou desde
o último release. Unidade com código novo e **mesmo** número é bug: suba com `dev bump`.

```powershell
uv run dev release api-gateway patch
```

Ele roda, em ordem: os testes do fecho e a suíte central; o gate de versão e as fronteiras; o bump
do app e a atualização do `uv.lock`; a gravação de `.releases/api-gateway.json` (o BOM, com a
versão e o sha256 do `src/` de cada unidade do fecho e o sha256 do `uv.lock`). Falhou em qualquer
etapa, para tudo.

Depois:

1. Commit `chore(release): api-gateway X.Y.Z` com o `pyproject.toml` do app, o `uv.lock` e o
   `.releases/api-gateway.json`. Abra o PR como na seção 4.
2. No merge, o `release.yml` confere o BOM contra o código que entrou, cria a tag
   `api-gateway@X.Y.Z` e o GitHub Release, e monta a imagem do app.
3. Se o `release.yml` reprovar com "o conteúdo do src/ não é o que o BOM aprovou", outra mudança
   entrou na `main` entre o seu release e o merge. Refaça o `dev release` a partir da `main` atual.

### 8.4 Promoção e volta

- **Mesma imagem** em homologação e produção. Nunca monte outra imagem para produção.
- **Plano de volta:** publicar a imagem da tag anterior. Se o release levou migração, o plano
  escrito na seção 8.2 diz se o `downgrade` roda antes ou se o código antigo convive com o schema
  novo.
- A publicação da imagem no registro e a atualização do ambiente ainda são manuais (seção 13).

---

## 9. Operação: a pilha local e o ambiente Azure

### 9.1 A pilha local (Docker Compose)

Os gates rodam na máquina, pelo `uv`. A **pilha** (banco, fila, API, worker, sites) roda em
container, para ninguém depender do Azure SQL ou do Node instalados na máquina
([ADR-0031](docs/kb/decisoes/0031-gates-na-maquina-pilha-em-container.md)).

```powershell
Copy-Item .env.example .env     # uma vez
make dev                        # monta as imagens e sobe tudo
make migrate                    # em outro terminal: aplica as migrações
make seed                       # popula um banco vazio com o catálogo de demonstração
```

Sem `make` no Windows, os alvos do [Makefile](Makefile) são uma linha de `docker compose` cada:
copie o comando de lá.

| Serviço | Endereço | O que é |
|---|---|---|
| `storefront` | http://localhost:3000 | a loja |
| `admin-dashboard` | http://localhost:3001 | o painel administrativo |
| `api-gateway` | http://localhost:8000 (`/docs` para a documentação da API) | a API |
| `worker` | sem porta | o `event-worker`, que consome os eventos |
| `prometheus` | http://localhost:9090 | as métricas |
| `grafana` | http://localhost:3002 | o painel "Revold — Visão Geral", já provisionado |
| `mssql`, `redis` | 1433 e 6379 | banco e fila |

- **Sem o `make seed`**, a loja sobe com a vitrine vazia e sem erro nenhum: parece que funciona, e
  não há dado para avaliar ([ADR-0022](docs/kb/decisoes/0022-processo-padrao-de-seed-semantico.md)).
  O seed nunca sobrescreve o que já existe.
- **Trocou dependência ou criou unidade?** A imagem precisa ser refeita: `make setup` (ou
  `docker compose build`). O `docker compose run` reaproveita a imagem velha sem avisar.
- **O código das unidades é montado por volume** no api-gateway e no worker. Editar um arquivo em
  `libs/`, `products/` ou no app recarrega a API sem rebuild. O worker não recarrega sozinho:
  `docker compose restart worker`.

### 9.2 Variáveis de ambiente

- A referência é o [.env.example](.env.example): cada variável tem o comentário de para que serve.
- Quem **lê** o ambiente é só o `settings.py` de cada app. Variável nova entra lá e no
  `.env.example`, no mesmo PR.
- O `environment:` do `docker-compose.yml` vence o `.env`. Antes de concluir que uma variável do
  `.env` "não funciona", confira se ela não está fixada no Compose.

### 9.3 Migrações

O histórico Alembic do banco da loja mora em `products/ecommerce/migrations_azure_sql/`. O banco é
um só, e as tabelas são de vários domínios: cada um declara as suas em `adapters/azure_sql/`, e
`revold_ecommerce.adapters.database` junta todas no `metadata` que o Alembic lê.

Mudou uma tabela? Mude o modelo primeiro e peça ao Alembic a migração, com a pilha de pé e as
migrações anteriores aplicadas (`make migrate`):

```powershell
docker compose run --rm api-gateway alembic revision --autogenerate -m "descricao curta"
```

**Leia o arquivo gerado antes de commitar.** O autogenerate escreve só a diferença entre o banco e
os modelos, e há o que ele não vê: renomear coluna vira apagar e criar (perde o dado), coluna
computada e índice full-text/vetorial (`TRANSLATE`, `VECTOR`/`VECTOR_DISTANCE`) precisam ser
escritos à mão. Toda migração tem `upgrade` e `downgrade`.

Domínio novo com tabela entra na lista de `revold_ecommerce/adapters/database.py`, no mesmo PR. O
teste `products/ecommerce/tests/test_migrations_match_models.py` confere as duas coisas: aplica
todas as migrações num banco vazio e reprova qualquer diferença com os modelos (seção 13,
item 13).

### 9.4 O ambiente Azure

O alvo é o Azure Container Apps
([ADR-0004](docs/kb/decisoes/0004-plataforma-de-execucao-azure.md)), descrito em
[deploy/terraform/](deploy/terraform/README.md). **O Terraform ainda não foi aplicado**, e não
existe ambiente publicado. O módulo `azure-sql` passa em `terraform validate` (Fase 7 do plano de
migração Postgres -> Azure SQL, docs internos); o módulo `azure-openai` ainda não (acompanha a
mesma pendência de validação dos demais — ver o README do Terraform). O que falta está na seção 13
e em [deploy/README.md](deploy/README.md).

---

## 10. Testes

```powershell
# Rotina: só o que a branch afeta
uv run dev test --affected -q

# A suíte inteira
uv run dev test -q

# Uma unidade, ou um arquivo
uv run pytest libs/domains/cart/tests -q
uv run pytest caminho/do/test_coisa.py -v
```

| Marcador | O que é | Roda por rotina? |
|---|---|---|
| (nenhum) | unitário: regra pura ou contra fake em memória | sim, sempre |
| `integration` | fala com Azure SQL, Redis ou um servidor de verdade em memória | **pula sozinho** sem a infraestrutura; roda no CI (Azure SQL) e com a pilha de pé |
| `contract` | confere a API contra os contratos em `products/ecommerce/contracts/api/`; hoje, a lista de rotas (seção 13, item 12) | sim |
| `eval` | o dataset comportamental do assistente de IA | a parte determinística, sim; o `test_llm_judge` só com `LLM_PROVIDER=azure-openai` e credencial real |

**Rodar os testes de integração na máquina:** suba só o banco e aponte os testes para ele.

```powershell
docker compose up -d mssql
$env:TEST_DATABASE_URL = "mssql+aioodbc://sa:revold_dev_only_1@localhost:1433/revold?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
$env:DATABASE_URL_SYNC = "mssql+pyodbc://sa:revold_dev_only_1@localhost:1433/revold?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
uv run alembic upgrade head
uv run pytest -m integration -q
```

Esses testes **gravam e apagam** dado. Nunca aponte `TEST_DATABASE_URL` para um banco que não seja
de teste.

**No Windows, não suba o Redis para os testes.** Com Redis alcançável em `REDIS_URL`, o teste de
round-trip do event-worker (`test_integration_worker.py`) deixa de pular, sobe um worker Celery
em subprocesso e **trava**: o pool `prefork` do Celery não funciona no Windows. Esse teste roda
em container (`make test-integration`).

**E2E (Playwright):** roda no CI sempre que a loja ou a API são afetadas. Na máquina, com a pilha
de pé (`make dev` e `make migrate`), o Playwright roda **fora** do container, como um cliente:

```powershell
pnpm install
pnpm --filter storefront exec playwright install chromium   # uma vez
make test-e2e                                               # ou: pnpm --filter storefront exec playwright test
```

A loja precisa estar em http://localhost:3000 e a API em http://localhost:8000. Com outras portas,
aponte `E2E_BASE_URL` e `E2E_API_BASE_URL`. O teste semeia o próprio produto pela API
([ADR-0020](docs/kb/decisoes/0020-testes-e2e-playwright.md)) e precisa de `NICK_WHATSAPP_NUMBER`
preenchido no `.env` (qualquer número serve), senão o checkout falha.

**Onde pôr o teste:** dentro da unidade (`libs/.../tests/`, `products/.../tests/`,
`apps/.../tests/`). A pasta `tests/` da raiz é a suíte central: `tests/architecture/` testa o
repositório inteiro, e `tests/support/revold_testing/` guarda as fábricas de dados compartilhadas
(Factory Boy e Faker, [ADR-0012](docs/kb/decisoes/0012-estrategia-de-testes-dados-realistas-e-evals.md)).

**Integração externa sem credencial:** todo adapter que fala com serviço de terceiro tem um adapter
de desenvolvimento e um teste em sandbox (`respx` para HTTP, `aiosmtpd` para SMTP, Azurite para
blob). O sandbox valida o **formato** documentado, não o comportamento real do serviço: diga isso
no PR.

---

## 11. Padrões de código

### 11.1 Fronteiras entre unidades

| Tipo | Onde | Pode depender de |
|---|---|---|
| **platform** | `libs/platform/` | `platform` |
| **integration** | `libs/integrations/` | `platform` |
| **capability** | `libs/capabilities/` (ainda sem unidade) | `platform`, `capability` |
| **domain** | `libs/domains/` | `platform`, `capability`, `integration` (só em `adapters/`) |
| **product** | `products/` | `platform`, `capability`, `integration`, `domain` |
| **app** | `apps/` | tudo, menos outro app. É o único que lê ambiente e monta adapters |
| **web** | `libs/web/` e os sites | `web` |

Dentro de domínio e produto, a ordem das camadas é `adapters -> application -> ports -> domain`. A
camada `domain/` não importa integração nem biblioteca de I/O. **Domínio não importa domínio**: o
que precisa de dois é do produto. O `uv run dev check` reprova o que fugir disso. Detalhes:
[docs/ARQUITETURA.md](docs/ARQUITETURA.md).

### 11.2 Gerados: nunca à mão

`.importlinter` e `.github/CODEOWNERS` saem de `uv run dev gen`. Mudou um `unit.yaml`? Rode o
`dev gen` e commite os dois juntos.

### 11.3 Configuração

Só o `settings.py` de um app lê variável de ambiente, pelo `revold_platform.configuration`. Lib e
produto recebem o valor por parâmetro. Um teste de arquitetura reprova `os.environ` fora do lugar.

### 11.4 Unidade nova

Código Python novo **não** vira repositório novo nem pasta solta; vira uma unidade aqui:

```powershell
uv run dev new <integration|capability|domain|product> <id> --depends-on <ids> --dry-run
uv run dev new app <produto>/<app> --runtime <fastapi-api|celery-worker> --dry-run
```

Sem o `--dry-run`, cria de verdade. Abra issue antes: unidade nova muda a arquitetura e passa pela
plataforma. Modelos: [tooling/README.md](tooling/README.md).

### 11.5 Lint e tipos

- `uv run ruff check .` é gate. `uv run ruff format <arquivo>` nos arquivos que você criar; não
  reformate arquivo herdado no mesmo PR de uma mudança de código (seção 13).
- `mypy` é gate: `# type: ignore` novo exige justificativa no PR.

---

## 12. Erros comuns e como sair deles

| Sintoma | Causa | O que fazer |
|---|---|---|
| `dev check`: "o src/ mudou ... e a versao continua X" | código mudou sem bump | `uv run dev bump <unidade> patch` (ou `minor`, seção 7.2) |
| `dev check`: gerados fora de dia | mexeu em `unit.yaml` sem regenerar | `uv run dev gen` e commite |
| `dev check`: contrato quebrado (`BROKEN`) | import proibido entre unidades ou camadas | mova o código ou declare o `depends_on`; pergunte antes de mexer em `unit.yaml` |
| `dev check`: "o pyproject.toml pede ... que faltam no depends_on" | dependência interna declarada num lugar só | declare no `unit.yaml` **e** no `pyproject.toml` |
| Teste de arquitetura: "importa unidade fora do depends_on" | o app importou uma unidade que não declara | declare no `unit.yaml` e no `pyproject.toml` do app |
| Teste de arquitetura: "le variavel de ambiente" | `os.environ` numa lib, no produto ou fora do `settings.py` do app | receba o valor por parâmetro; leia no `settings.py` |
| `ModuleNotFoundError` só dentro do container | a imagem é anterior à unidade ou à dependência nova | `docker compose build` (ou `make setup`) |
| Variável do `.env` sem efeito na pilha | ela está fixada no `environment:` do `docker-compose.yml` | tire de lá, ou mude lá |
| Hook não rodou no commit | hooks não instalados | seção 2.3 |
| Push recusado com `GH013` e menção a *push protection* ou *secret* | o GitHub achou um token num commit da sua branch | tire o segredo do arquivo **e do commit** (no último commit: corrija, `git add` e `git commit --amend`); se o segredo era real, ele já saiu da sua máquina: siga o [SECURITY.md](SECURITY.md). Nunca use o botão de liberar o push para segredo de verdade |
| Commit falhou depois de o hook "consertar" | o hook alterou o arquivo | `git add` e commite de novo |
| PR sem botão de merge | falta `CI OK` ou aprovação, ou o PR é draft | veja os checks e o "Ready for review" |
| Aprovação sumiu | push novo derruba aprovação | peça a revisão de novo |
| `release.yml`: "nao e o que o BOM aprovou" | a `main` andou entre o `dev release` e o merge | refaça o `dev release` a partir da `main` atual |
| `test_migrations_match_models`: "o banco migrado e os modelos divergem" | mudou um modelo sem migração (ou o contrário), ou a tabela nova não está em `revold_ecommerce.adapters.database` | gere a migração com `--autogenerate` (seção 9.3), leia, e commite junto; a lista do erro é o que falta |
| Teste que confere log vê o log vazio, só no CI ou só numa ordem de execução | algo chamou `logging.config.fileConfig` no processo do pytest antes dele (o `env.py` do Alembic chama), e isso desliga todo logger que já existia | ao chamar o Alembic por código, passe `config.attributes["configure_logger"] = False` |
| `pytest -m integration` trava no Windows, sem saída | há um Redis alcançável e o teste do worker subiu um Celery com pool `prefork` | encerre o processo, derrube o Redis (`docker compose stop redis`) ou rode em container |
| `pnpm -r build` falha com `ENOENT ... rename` no Windows | `pnpm -r` inclui a raiz, cujo script chama `pnpm -r` de novo: cada site builda duas vezes ao mesmo tempo | use `pnpm build` e `pnpm lint` (os scripts da raiz) |
| PowerShell: "executar software de fornecedor não confiável" | política `AllSigned` | seção 2.1 e a [nota do Windows](docs/kb/ambiente-local-no-windows.md) |
| `'pre-commit' is not recognized`, mas o `uv tool install` diz "already installed" | a pasta de ferramentas do uv (`%USERPROFILE%\.local\bin`) não está no PATH | `uv tool update-shell` e abra um terminal novo |
| `winget install --id GitHub.cli` termina com `exit code: 1602` | o instalador MSI pede administrador | instale o zip portátil (seção 2.1.1) |

---

## 13. Pontos em aberto (o que ainda não protege)

Esta seção diz onde a proteção descrita acima **ainda não está completa**, para ninguém confiar
num gate que não existe.

1. **Gate de versão sem ponto de comparação até o primeiro release.** O `dev check` compara o
   `src/` de cada unidade com o BOM do último release de cada app (`.releases/<app>.json`). Nenhum
   app tem release ainda. O gate avisa isso a cada rodada ("ainda nao tem release: nada a
   comparar") e não reprova nada.

   **Decidido em 2026-11-14: fica assim.** Enquanto nada foi publicado, não há número para
   proteger, e ninguém precisa subir versão à mão. O gate liga sozinho no primeiro
   `uv run dev release` de cada app: é ele que grava o BOM. A partir daí, a seção 7.2 vale para
   as unidades daquele app.
2. **O ruleset ainda não foi aplicado.** As regras da seção 5.4 só valem depois de um administrador
   rodar `scripts/setup-rulesets.sh --apply`. Sem argumento, o script mostra o que faria. Até lá,
   a `main` só é protegida pelo hook local.

   **Decidido em 2026-11-14: aplicar o ruleset completo** (PR obrigatório, `CI OK`, aprovação de
   um dono, sem bypass), **logo depois que a reorganização do monorepo entrar na `main`.** Não
   antes: é esse merge que leva para a `main` o `ci.yml` com o job `CI OK` e o CODEOWNERS. Quem
   roda é o dono do repositório, o único com permissão de administrador. Antes de aplicar, o
   item 3 precisa estar resolvido.
3. **Os donos do CODEOWNERS precisam ser conferidos.** `@SamuelSMatos` e `@dmourans` precisam ser
   colaboradores do repositório; nome errado é ignorado pelo GitHub sem aviso.

   **Decidido em 2026-11-14: mantêm-se os dois donos, conferidos antes de aplicar o ruleset.**
   `@dmourans` já é colaborador (informado pelo dono da conta em 2026-11-14). Falta a prova no
   GitHub, assim que a branch da reorganização estiver no remoto. O GitHub lista os erros do
   CODEOWNERS de uma branch, e a lista precisa vir vazia:

   ```powershell
   gh api "repos/SamuelSMatos/revold/codeowners/errors?ref=<branch>"
   ```

   Dono sem permissão de escrita aparece ali como "Unknown owner". Com a lista vazia, o item 2
   pode ser aplicado.
4. **Hooks dependem de cada pessoa instalar.** Nada obriga o `pre-commit install`: o Git não deixa
   um projeto instalar hook sozinho na máquina de ninguém.

   **Decidido em 2026-11-14: o CI roda os mesmos hooks.** Antes, o que só o hook conferia
   (YAML, JSON e TOML quebrados, marcador de conflito, arquivo grande, espaço no fim da linha,
   CRLF) chegava na `main` sem ninguém ver, e o `orders.yaml` ficou inválido assim. Agora o job
   "Hooks do pre-commit" roda os hooks de commit em todos os arquivos, ligado ao `CI OK`. Instalar
   os hooks (seção 2.3) continua sendo o combinado do time: é o jeito de descobrir em segundos, e
   não no PR.
5. **Hook e CI divergem** em `bandit`, `pip-audit`, frontend e imagens, que só rodam no CI (seção
   5.3). Isso é de propósito: são lentos ou precisam de internet.

   **Detector de segredo. Decidido em 2026-11-14: ligar o do próprio GitHub.** A busca do CI só
   procura 9 nomes de variável atribuídos a um valor no código: não pega token colado num
   documento, num JSON ou com outro nome. O *secret scanning* com *push protection* do GitHub
   reconhece o formato dos tokens de centenas de serviços e **recusa o push** que traz um deles.
   É grátis em repositório público. Quem liga é o dono do repositório, no mesmo
   `scripts/setup-rulesets.sh --apply` do item 2 (ou à mão, em *Settings -> Code security*). A
   busca por nome do CI continua como segunda camada. Até ser ligado, vale só ela.
6. **`ruff format` não é gate.** 155 arquivos herdados não estão no formato do `ruff format`
   (medido em 2026-11-15; os arquivos escritos na reorganização já estão). Ligar o gate de uma vez
   reformataria cada arquivo no primeiro toque, misturando arrumação com mudança de verdade.

   **Decidido em 2026-11-15: um PR só de formatação, logo depois que a reorganização entrar na
   `main`.** Ensaiado numa cópia do repositório: `ruff format .` muda os 155 arquivos, e depois
   disso o `ruff check`, o `dev check` (com mypy) e os 861 testes continuam passando. O roteiro:

   1. Issue `chore` e branch a partir da `origin/main`.
   2. `uv run ruff format .`, e nada mais de código no mesmo commit.
   3. No mesmo PR, ligar o gate: um hook `ruff-format` (`uv run ruff format --check .`) no
      `.pre-commit-config.yaml` e o mesmo comando no job de lint do `ci.yml`.
   4. Título: `chore: formata o repositorio com ruff format`. Na revisão, o que prova que nada
      mudou de comportamento é o `CI OK` verde, não a leitura linha a linha.
   5. Depois do squash merge, um PR pequeno cria o `.git-blame-ignore-revs` com o hash do commit
      de formatação na `main`. Só dá para fazer depois, porque o hash do squash só existe no
      merge. O GitHub lê esse arquivo sozinho; na máquina, uma vez:
      `git config blame.ignoreRevsFile .git-blame-ignore-revs`.
7. **A publicação é manual.** O `release.yml` confere o BOM, cria a tag e monta a imagem, mas só a
   envia ao registro com a variável de repositório `IMAGE_PUBLISH_ENABLED=true`. Levar a imagem ao
   Azure e atualizar o Container App não está automatizado, e o Terraform nunca foi aplicado: o
   Container App aponta para uma imagem de exemplo e não há registro de imagem no Azure.

   **Decidido em 2026-11-15: a publicação fica desligada até o ambiente existir.** O release
   continua conferindo o BOM, criando a tag e montando a imagem, o que prova que cada versão é
   montável. Ligar a publicação e o deploy (homologação e produção, com aprovação para produção)
   é uma issue própria, aberta quando o Terraform for aplicado ([deploy/README.md](deploy/README.md)).
8. **Os sites ficam fora do release pelo tooling.** `dev release` e o BOM só cobrem app Python: não
   há BOM nem tag para o `storefront` e o `admin-dashboard`, e a versão no `package.json` deles
   ninguém sobe.

   **Decidido em 2026-11-15: o CI monta a imagem dos sites; o release deles espera.** O job
   "Imagem `<site>`" roda o `docker build` dos dois sempre que a parte web é afetada, e pega um
   `Dockerfile` quebrado no PR, inclusive o que o `make dev` usa. Release, BOM e tag dos sites
   ficam para quando for decidido onde eles rodam em produção: o README do Terraform cita Azure
   Static Web Apps ou Vercel, e lá talvez nem se use a imagem.
9. **Os sites quase não têm teste automatizado.** O `admin-dashboard` não tem teste, e
   `libs/web/ui` tem o Vitest configurado e nenhum arquivo de teste.

   **Decidido em 2026-11-15: a prova de cliente da loja roda no CI.** O job "E2E (Playwright)"
   sobe banco, fila, API e loja e roda os 2 testes (carrinho e checkout pelo WhatsApp; busca)
   sempre que a loja ou a API são afetadas. Ensaiado na máquina: os 2 passam, e com o checkout
   quebrado de propósito o primeiro reprova. No caminho, o `make test-e2e` foi consertado: ele
   rodava o Playwright dentro de um container novo, onde nem a loja nem a API respondem, e
   procurava o navegador numa pasta que só existia no ambiente em que os testes foram escritos.
   Testes do painel e dos componentes são trabalho novo, para issues próprias.
10. **Ainda há regra de negócio nos routers do api-gateway.** A orquestração que estava em módulos
    próprios foi para o produto. A que está escrita dentro das funções de rota continua lá, em
    dois lugares conhecidos:

    - **o checkout** (`routers/cart.py`): reserva e devolve estoque, monta o link do WhatsApp,
      registra o pedido e publica o evento, passos de cinco domínios numa função de rota;
    - **"pagamento confirmado"**: marcar o pedido como pago e dar baixa no estoque está escrito
      duas vezes, no webhook do gateway (`routers/payments.py`) e no botão do painel
      (`routers/orders.py`). Mudou um, mude o outro no mesmo PR.

    **Decidido em 2026-11-15: fica assim por enquanto.** Regra **nova** que cruza domínios vai
    para o produto (`revold_ecommerce.application`), e a revisão cobra isso. As duas receitas
    antigas ficam nas rotas até alguém precisar mexer nelas. Nenhum gate pega regra na rota: é
    revisão humana.
11. **O nome do cliente piloto está no código, inclusive em `libs/`.** Medido em 2026-11-15: 65
    arquivos, 20 deles no `src/` de libs, contra a regra 8 da seção 1. No site é esperado (ele é a
    loja do cliente); nas libs, três casos mudam comportamento:

    - o prompt do assistente (`revold_ai_assistant.application.use_cases._build_system_prompt`)
      se apresenta como "assistente virtual da loja da Nick": outra loja usando a lib teria o
      nome errado na boca do robô;
    - as variáveis `NICK_WHATSAPP_NUMBER` e `NICK_NOTIFICATION_EMAIL`, lidas pelas libs
      `notification` e `communication`;
    - a resposta do provedor de LLM de desenvolvimento.

    **Decidido em 2026-11-15: tirar o nome das libs, num PR próprio depois da reorganização.** O
    roteiro:

    1. O assistente recebe o nome da loja por parâmetro. Quem chama (a rota do assistente) lê o
       `store_name` da configuração da loja e entrega; o domínio não importa outro domínio.
    2. As variáveis ganham nomes neutros (`STORE_WHATSAPP_NUMBER`, `STORE_NOTIFICATION_EMAIL`).
       O `settings.py` de cada app aceita o nome antigo por um tempo, com aviso no log, para
       nenhum `.env` existente quebrar. `.env.example`, `docker-compose.yml` e o CI mudam juntos.
    3. Comentários e textos das libs trocam "a Nick" por "a loja".
    4. Um teste de arquitetura reprova o nome do cliente dentro de `libs/`, e a regra 8 passa a
       ser conferida por ferramenta, e não só por revisão.
    5. O site fica com o nome. Tirá-lo do código dele (título e textos lidos da configuração da
       loja) é outra conversa.
12. **O teste de contrato só confere as rotas, não os campos.** Os contratos em
    `products/ecommerce/contracts/api/` são o cardápio que os sites consultam.

    **Decidido em 2026-11-15: conferir já os nomes das rotas.** O teste
    `apps/ecommerce/api-gateway/tests/test_contract_routes.py` (marcador `contract`) compara o
    método e o caminho de cada rota da API com os dos contratos, e reprova rota sem contrato e
    contrato de rota que não existe. Medido ao ligar: as 40 rotas dos contratos batem uma a uma
    com a API; `/health` e `/metrics` ficam fora, numa lista de exceções com motivo. Ensaiado com
    uma rota nova sem contrato: o teste reprova. O que continua sem conferência são os **campos**
    de cada requisição e resposta, que exigem ferramenta nova ou um teste por rota: issue
    própria. Caso real do que só a conferência de conteúdo pegaria: o `orders.yaml` ficou com um
    YAML inválido desde que nasceu, e só apareceu quando o hook `check-yaml` passou a ler o
    arquivo.
13. **As migrações não eram conferidas contra os modelos.** O `env.py` do Alembic só registrava
    os modelos do catálogo, então o autogenerate não enxergava os outros domínios e nenhum gate
    avisava quando um modelo mudava sem migração.

    **Decidido em 2026-11-15: conferir no CI.** Medido antes da mudança, num banco migrado até a
    última versão: o `alembic revision --autogenerate` mandaria apagar 7 tabelas (as de todos os
    domínios fora o catálogo), 8 índices e 1 restrição de unicidade. As tabelas, porque o
    `env.py` não as via; os índices e a restrição, porque as migrações os criaram e os modelos
    nunca os declararam. Quem confiasse no autogenerate apagaria pedidos e cobranças. O que mudou:

    - `revold_ecommerce.adapters.database` junta os modelos dos 7 domínios com tabela, e o
      `env.py` lê o `metadata` dele (o produto passou a declarar `identity`, `payments` e
      `postgres` no `depends_on`);
    - os modelos de `catalog`, `identity`, `orders` e `payments` ganharam os índices e a restrição
      que o banco já tinha. Nenhuma migração nova: o banco não muda;
    - o teste `products/ecommerce/tests/test_migrations_match_models.py` (marcador `integration`)
      cria um banco vazio, aplica todas as migrações e reprova qualquer diferença com os modelos.
      Roda no job de testes do CI, com o Azure SQL do container; na máquina, pula sem banco.

    Ensaiado no Postgres com pgvector: o teste passa, o `alembic check` responde "No new upgrade
    operations detected" e, com uma coluna nova no modelo de pedido e sem migração, o teste
    reprova apontando a coluna. Com isso, a seção 9.3 passou a usar o autogenerate.

---

## 14. Ajuda, segurança e base de conhecimento

- **Dúvida ou travou:** [SUPPORT.md](SUPPORT.md). Antes de perguntar, procure em
  [docs/kb/](docs/kb/README.md) e nas [decisões](docs/kb/decisoes/README.md).
- **Vulnerabilidade ou segredo vazado:** [SECURITY.md](SECURITY.md). **Nunca** issue pública.
- **Convivência:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Descobriu algo que custou para achar** (um gotcha, uma decisão)? Escreva a nota na KB no
  mesmo PR, seguindo a [regra de captura](AGENTS.md#a-regra-de-captura-da-kb). Nunca ponha valor de
  variável, credencial ou caminho da sua máquina em nota.
