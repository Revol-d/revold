---
tags: [ambiente, onboarding, windows, uv]
status: ativo
escopo: plataforma
resumo: Os atritos de montar e usar o ambiente local no Windows corporativo — politica AllSigned, uv fora do PATH, o python do PATH que nao enxerga as unidades, a ferramenta do uv tool install fora do PATH, o GitHub CLI que o winget so instala com admin e o pnpm -r que builda cada site duas vezes
cobre: [pyproject.toml, .pre-commit-config.yaml]
---

# Ambiente local no Windows (máquina corporativa)

> Leia antes de montar o ambiente numa máquina nova. O passo a passo canônico é a seção 2 do
> [CONTRIBUTING.md](../../CONTRIBUTING.md); esta nota cobre só o que trava no caminho e não está
> óbvio lá.
>
> **De onde vem cada item.** Os atritos 1 a 5 são a experiência do time em máquinas Windows com
> política de TI, registrada em outro monorepo; valem para qualquer projeto com `uv` e não foram
> reproduzidos de novo neste repositório. O atrito 6 foi medido aqui, em 2026-11-14.

## 1. `MachinePolicy = AllSigned` bloqueia a ativação do venv

Numa máquina corporativa, `Get-ExecutionPolicy -List` pode mostrar `MachinePolicy = AllSigned`,
imposto por Group Policy. **Não dá para sobrepor**: `Set-ExecutionPolicy -Scope CurrentUser` roda
sem erro e a política efetiva continua `AllSigned`, porque `MachinePolicy` vence todos os escopos.

Consequência: scripts `.ps1` sem assinatura não rodam. O que dispara na prática é o VS Code tentando
**ativar o `.venv` automaticamente** ao abrir um terminal: cai um prompt "executar software de
fornecedor não confiável" a cada terminal novo.

**Isso não trava o trabalho.** O `uv` é um `.exe`, não um script, e roda sob qualquer política. E
`uv run <comando>` **não precisa** de venv ativado.

**Solução:** desligar a ativação automática no `settings.json` do usuário (VS Code):

```json
"python.terminal.activateEnvironment": false
```

Trabalhe sempre por `uv run` (`uv run pytest`, `uv run dev check`). Não dependa de `.venv` ativado.

## 2. `uv` fora do PATH depois de instalar

Recém-instalado, o `uv` costuma não ser reconhecido no terminal até **fechar e reabrir** o terminal
(e o VS Code inteiro, que herda o ambiente do processo pai). Se ainda assim não aparecer:

- Instalado por `winget install --id=astral-sh.uv -e`: o binário vai para a pasta de links do
  WinGet, já no PATH do usuário após reabrir.
- Instalado por `pip install --user uv`: o `uv.exe` fica em `%APPDATA%\Python\Python3XX\Scripts`,
  que o `pip --user` **não** põe no PATH. Adicione (comando direto, não script: passa pela
  política):

  ```powershell
  [Environment]::SetEnvironmentVariable("Path", "$env:APPDATA\Python\Python314\Scripts;" + [Environment]::GetEnvironmentVariable("Path","User"), "User")
  ```

  Ajuste `Python314` para a versão que o `pip --user` usou. Reabra o VS Code e teste `uv --version`.

## 3. O `python` do terminal não enxerga as unidades do repositório

Rodar algo do monorepo com `python -m api_gateway.seed` ou `python -c "import revold_catalog"`
falha com `ModuleNotFoundError`. O motivo não é o repositório: o `python` do PATH aponta para a
instalação **global** do Windows (que pode nem ser a 3.12), e as unidades estão instaladas no
`.venv` do projeto.

**Solução:** `uv run <comando>`, que resolve o ambiente e a versão do Python sozinho:

```powershell
uv run python -c "import revold_catalog; print('ok')"
uv run pytest libs/domains/catalog/tests -q
```

Sem `uv` à mão, `.\.venv\Scripts\python.exe` é equivalente.

## 4. `pre-commit` "already installed" mas "not recognized"

`uv tool install pre-commit` responde `` `pre-commit` is already installed ``, e logo depois
`pre-commit --version` dá `'pre-commit' is not recognized as an internal or external command`.

O `uv tool install` põe o executável na pasta de ferramentas do uv, `%USERPROFILE%\.local\bin`
(`uv tool dir --bin` mostra qual é). Ele **não** acrescenta essa pasta ao PATH.

**Solução**, uma vez por máquina:

```powershell
uv tool update-shell
```

Ele grava a pasta no PATH do usuário. Feche e reabra o terminal (e o VS Code inteiro) e confira com
`pre-commit --version`. Vale para qualquer ferramenta instalada por `uv tool install`.

Sem os hooks ligados (`pre-commit install` e `pre-commit install --hook-type pre-push`), nenhuma
barreira local roda e o erro só aparece no CI.

## 5. `winget install GitHub.cli` falha com `1602` sem admin

O `winget` baixa o instalador MSI do GitHub CLI, que instala para todos os usuários da máquina e
por isso pede elevação. Sem administrador o pedido é recusado e o log registra
`Installation success or error status: 1602. User cancelled installation.`

**Solução:** a versão portátil (zip oficial do release), extraída no perfil e posta no PATH do
usuário. Não precisa de admin. O bloco de comandos está na seção 2.1.1 do
[CONTRIBUTING.md](../../CONTRIBUTING.md).

Se a máquina bloquear executável em pasta do usuário (política de aplicativos), aí só o TI resolve;
o fluxo de issue e PR funciona pelo site.

## 6. `pnpm -r build` falha com `ENOENT ... rename` (2026-11)

`pnpm -r lint` e `pnpm -r build` na raiz terminam em erro de arquivo
(`EPERM: operation not permitted, rename` ou `ENOENT: no such file or directory, rename ...\.next\...`),
e os mesmos comandos passam quando rodados um site por vez.

Causa: com `-r` na linha de comando, o pnpm inclui o pacote da raiz. O script `lint` (e o `build`)
da raiz é `pnpm -r lint`, então cada site é lintado e buildado **duas vezes ao mesmo tempo** sobre a
mesma pasta `.next`. No Linux a corrida costuma passar; no Windows, a renomeação de arquivo falha.

**Solução:** use os scripts da raiz, sem `-r`:

```powershell
pnpm lint
pnpm build
```

Ou um site por vez: `pnpm --filter storefront build`. O CI usa `pnpm lint` e `pnpm build`.
