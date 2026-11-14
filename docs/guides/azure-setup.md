# Guia de Infraestrutura — Configuração do Azure

Este guia cobre a configuração de **identidade, governança, billing e segurança** no Portal do Azure para o time (hoje duas pessoas: uma focada em infra, outra em análise/refatoração do código). Ele complementa, mas não substitui, ADR-0004 (plataforma de execução) e ADR-0008 (CI/CD) — a regra de lá continua valendo: **nenhum recurso de workload é criado manualmente pelo Portal**, tudo via Terraform (`iac/terraform/`). O Portal entra só para o que não é modelável como recurso de app: usuários, billing, policy, Defender.

Cada comando abaixo vem com uma explicação logo depois, linha por linha — a ideia é que dê pra rodar sem ter que adivinhar o que uma flag faz ou copiar sem entender.

## Conceitos — antes de abrir o Portal

| Termo | O que é | Uso aqui |
|---|---|---|
| **Tenant (Entra ID)** | Diretório de identidade | Separa *organizações*. Não precisa de tenant novo pra separar dev/hml/prod — isso é Resource Group. |
| **Subscription** | Unidade de billing + boundary de política/RBAC | Opcional pra isolamento mais forte entre ambientes; não necessário no estágio atual. |
| **Resource Group** | Agrupamento de recursos dentro de uma subscription | É o que `iac/terraform/modules/network/main.tf` já usa (`rg-${project_name}-${environment}`). |
| **Role RBAC** (Contributor, Owner) | Permissão pra *gerenciar recursos* | O que o segundo dev precisa pra criar/gerenciar recursos de dev. |
| **Role de Billing** (Billing Reader, Account Owner) | Permissão pra *ver/gerenciar custo e pagamento* | Separado do RBAC — Contributor não implica acesso a billing, mas em várias contas o custo fica visível por padrão a menos que isso seja desligado explicitamente (Passo 2). |
| **Login Entra ID vs. e-mail real** | Entra ID dá uma *conta* (`pessoa@dominio.onmicrosoft.com`), não uma caixa que recebe mensagem | Suficiente pra acesso ao Portal/CLI. E-mail que recebe mensagem de verdade é Microsoft 365/Google Workspace — serviço separado, pago, exige domínio próprio. |

### ⚠️ Armadilha comum: tenant/subscription errado

Um tenant Entra ID novo nasce **sem nenhuma subscription dentro dele**. Se você criar uma conta (admin ou dev) do zero — um sign-up novo, não um usuário dentro do tenant que já existe — ela cai sozinha num tenant vazio ("Default Directory"), sem enxergar a subscription onde o resto do projeto vive. `az login` deixa isso óbvio: se aparecer `No subscriptions found for <usuário>`, essa conta está no tenant errado.

Antes de criar qualquer recurso, sempre confirme em qual subscription/tenant você está:

```powershell
az login
az account list --output table
az account set --subscription "<nome-ou-id-da-subscription>"
az account show --output table
```

- `az login` — abre o navegador, você autentica com a conta Microsoft/Entra ID desejada, e o CLI guarda um token de sessão local. Se você já tinha feito login com outra conta antes, isso troca a sessão ativa.
- `az account list --output table` — lista **todas** as subscriptions que essa conta consegue enxergar, em qualquer tenant, numa tabela legível (nome, ID, tenant, se é a "IsDefault"). Se vier vazio, a conta logada não tem acesso a nenhuma subscription — é o sintoma do parágrafo acima.
- `az account set --subscription "..."` — define qual dessas subscriptions é a "ativa" pra todos os comandos seguintes do CLI (pode usar o nome ou o GUID da subscription, ambos aparecem no `list`). Sem isso, o CLI usa a subscription marcada `IsDefault: true`, que pode não ser a que você quer.
- `az account show --output table` — confirma qual subscription/tenant ficou ativa depois do `set`, antes de criar qualquer coisa.

### Onde encontrar os roles builtin certos no Portal

Isso vale pros Passos 4 e 5: a tela **Access control (IAM) → Add role assignment** tem duas abas:

- **"Funções de trabalho" / "Job function roles"** — ~1000 roles, cada um específico de um serviço do Azure (`Azure AI Developer`, `Oracle.Database Owner`, etc.). A busca por texto aqui bate na descrição inteira, não só no nome — por isso buscar "owner" devolve lixo.
- **"Funções de administrador privilegiadas" / "Privileged administrator roles"** — lista curta e fixa: `Owner`, `Contributor`, `Reader`, `User Access Administrator` (às vezes `RBAC Administrator`). **É essa aba que você quer** sempre que o objetivo for um dos 4 roles genéricos citados neste guia — sem precisar buscar nada, a lista já é pequena.

## Passo 1 — Identidade (Entra ID)

Não é necessário criar um tenant novo — o tenant atual já existe (criado junto com a primeira subscription). Criar um tenant extra é gratuito (Entra ID Free), mas resolve um problema diferente (isolar identidade de outra organização, não separar ambientes de um mesmo projeto). **Não crie uma conta Microsoft do zero para o admin** — isso gera um tenant novo e vazio (ver armadilha acima); crie a conta como usuário *dentro* do tenant que já tem a subscription.

1. Portal → **Microsoft Entra ID** → **Users** → **New user** → **Create new user** (não "Invite external user" — Member, não Guest, para o segundo dev poder ser dono de recursos sem restrição de guest).
2. Nome de usuário: `pessoa@dominio.onmicrosoft.com` (domínio padrão grátis) ou domínio próprio verificado, se houver.
3. Não atribuir nenhuma role de diretório alta (Global Admin) à conta nova.
4. Ativar MFA para as duas contas: **Microsoft Entra ID → Properties → Manage security defaults → Enable** (MFA obrigatório pra todo o tenant, grátis, sem precisar de Conditional Access P1/P2). Na prática, no próximo login de cada conta o Azure vai pedir pra registrar um método (normalmente o app Microsoft Authenticator no celular) antes de liberar o acesso.

## Passo 2 — Isolar billing

RBAC e billing são sistemas separados — "ele só tem Contributor" não é suficiente por padrão em várias contas.

1. Portal → **Cost Management + Billing** → selecione a **Billing Account** → **Policies** (nome exato varia conforme o tipo de contrato — *Microsoft Customer Agreement* é o mais comum em conta nova paga por cartão).
2. Desative a opção equivalente a **"Azure RBAC access to cost management data"**. Com isso desligado, só quem tem role de billing explícita vê custo — Contributor/Owner em recurso não basta.
3. Garantir que a conta do segundo dev não recebe nenhuma role em **Access control (IAM)** no nível da Billing Account/Billing Profile — só nas subscriptions/resource groups (Passo 4).
4. Configurar um **Budget**: Portal → **Cost Management + Billing** → **Cost Management** → **Budgets** → **Add** → defina um valor mensal e um e-mail de alerta (ligado ao Action Group do Passo 8) pra ser avisado antes de qualquer surpresa de fatura.

## Passo 3 — Separação de ambientes

Recomendado para o estágio atual (2 pessoas, 1 cliente): **uma subscription**, com os três Resource Groups que o Terraform já cria (`rg-revold-dev`, `rg-revold-staging`, `rg-revold-production` — ver `var.environment` em `iac/terraform/variables.tf`). Ter mais Resource Groups não tem custo. **Não crie esses três RGs manualmente** — o módulo `network` (`iac/terraform/modules/network/main.tf`, recurso `azurerm_resource_group.this`) já faz isso no primeiro `terraform apply`; a única exceção de bootstrap manual é a RG do state remoto, no Passo 6.

Se no futuro for necessário isolamento mais forte (cota separada, política diferente por ambiente), criar uma segunda subscription (`revold-nonprod` / `revold-prod`) no mesmo tenant — criar subscription é grátis, só os recursos usados são cobrados. Não é necessário decidir isso agora.

## Passo 4 — RBAC

- **Conta admin** (infra): `Owner` no nível da subscription (aba "Funções de administrador privilegiadas", ver seção acima) — é essa identidade (via pipeline, não localmente) que aplica Terraform contra produção. `Owner` é a soma de `Contributor` (criar/gerenciar recurso) + `User Access Administrator` (atribuir role a outras contas, o que essa conta precisa fazer no restante deste passo e no Passo 5).
- **Conta do segundo dev**: role **Contributor** (mesma aba "Funções de administrador privilegiadas") atribuída só nos Resource Groups `rg-revold-dev` (e `staging`, se também responsável por homologação) — nunca em `rg-revold-production` nem na subscription inteira.

Passo a passo no Portal pra atribuir (mesmo fluxo pros dois casos acima, mudando só o escopo e a role):

1. Navegue até o escopo certo: **subscription** inteira (conta admin) ou o **Resource Group** específico, ex. `rg-revold-dev` (conta do dev).
2. **Access control (IAM)** → **Add** → **Add role assignment**.
3. Aba **Função**: clique em **"Funções de administrador privilegiadas"** e escolha `Owner` ou `Contributor`. **Próximo**.
4. Aba **Membros**: **Select members** → busque pelo e-mail da conta (admin ou dev) → selecione → **Select**.
5. Aba **Examinar + atribuir**: confira escopo + role + membro, e clique em **Atribuir**.

## Passo 5 — Pipeline dev → hml → prod (OIDC)

ADR-0008 já decidiu deploy via GitHub Actions com OIDC (sem secret de longa duração) — falta implementar o workflow. Dá pra fazer pelo Portal (App registrations) ou via CLI — abaixo o caminho CLI, com cada comando explicado, repetido uma vez por ambiente (`dev`, `staging`, `prod`):

```powershell
az ad app create --display-name "sp-revold-dev" --query appId -o tsv
```
- Cria um **App Registration** no Entra ID (a "identidade" que o GitHub Actions vai assumir) chamado `sp-revold-dev`.
- `--query appId -o tsv` filtra a resposta (que normalmente é um JSON grande) pra devolver só o `appId` (GUID), em texto puro — **guarde esse valor**, vai ser usado em todos os comandos seguintes e nos secrets do GitHub.

```powershell
az ad sp create --id <appId-copiado-acima>
```
- O `app create` só cria a "aplicação"; esse comando cria o **Service Principal** associado a ela — é o objeto que de fato recebe permissões (role assignments) dentro de uma subscription. Sem esse passo, o app existe mas não consegue ser "convidado" pra nenhum Resource Group.

```powershell
az ad app federated-credential create --id <appId> --parameters '{\"name\": \"github-actions-dev\", \"issuer\": \"https://token.actions.githubusercontent.com\", \"subject\": \"repo:SamuelSMatos/revold:environment:dev\", \"audiences\": [\"api://AzureADTokenExchange\"]}'
```
- Configura a **federação OIDC**: diz ao Entra ID "confie em tokens assinados pelo GitHub Actions (`issuer`), desde que o token seja especificamente do repositório/ambiente certo (`subject`)". É isso que elimina a necessidade de um client secret — o GitHub Actions troca esse token por um token Azure válido na hora do deploy.
  - `name`: só um rótulo pra identificar essa credencial depois (pode repetir o padrão `github-actions-<ambiente>`).
  - `issuer`: valor **fixo**, sempre `https://token.actions.githubusercontent.com` — é o emissor de todo token OIDC do GitHub Actions.
  - `subject`: precisa bater **exatamente** com `repo:<org-ou-usuário>/<repositório>:environment:<nome-do-ambiente>` — troque `SamuelSMatos/revold` e `dev` pelos valores reais; é essa string que amarra a credencial a um GitHub Environment específico (Passo 4 abaixo).
  - `audiences`: valor **fixo**, sempre `api://AzureADTokenExchange` — é a audiência que o Azure espera ver no token.

```powershell
az role assignment create --assignee <appId> --role Contributor --scope /subscriptions/<subscription-id>/resourceGroups/rg-revold-dev
```
- Dá ao Service Principal a mesma role `Contributor` que o dev humano tem, mas escopada só ao Resource Group `rg-revold-dev` — é o que permite o pipeline rodar `terraform apply` nesse RG.
- `--assignee` aceita o `appId` direto. `--scope` é o caminho completo do recurso — troque `<subscription-id>` pelo valor que apareceu no `az account show` (Passo 0).

Depois de repetir os 4 comandos acima pra `staging` e `prod` (trocando o nome do app e o RG de destino):

1. GitHub → **Settings → Environments** → criar `dev`, `staging`, `production` (o nome precisa bater com o `subject` da federated credential). Em `production`, configurar **required reviewers** (aprovação manual antes do apply rodar).
2. Em cada Environment do GitHub, guardar como variável (não precisa ser secret, já que não é um valor sigiloso) o `appId` daquele ambiente, mais o `tenant-id` e `subscription-id` (saem de `az account show`).
3. Criar `.github/workflows/cd.yml` (ainda não existe — hoje `ci.yml` só testa) usando `azure/login@v2` com `client-id`/`tenant-id`/`subscription-id` (OIDC, sem `client-secret`), rodando `terraform plan` em PR e `terraform apply` só após merge, por ambiente.

## Passo 6 — Testar o Terraform na prática

O backend remoto está comentado em `iac/terraform/providers.tf` — sem ele, duas pessoas aplicando Terraform correm o risco de sobrescrever o state uma da outra (cada `apply` local sobrescreve um arquivo `terraform.tfstate` só na sua própria máquina).

### 6.1 — Criar o storage account que vai guardar o state (bootstrap manual, única exceção)

O state não pode ser guardado dentro de um recurso que o próprio Terraform ainda vai criar — por isso esse bootstrap é feito direto no CLI, uma vez só, por quem for configurar o backend (normalmente a conta admin).

```powershell
az storage account check-name-availability --name revoldtfstate
```
- Nome de storage account precisa ser **globalmente único em todo o Azure** (não só na sua subscription), só letras minúsculas e números, 3 a 24 caracteres. Esse comando confere isso *antes* de tentar criar — devolve um JSON com `"nameAvailable": true/false` e, se `false`, o motivo. Se vier `false`, escolha outro nome (ex.: `revoldtfstate2026`) e repita antes de seguir.

```powershell
az group create -n rg-revold-tfstate -l brazilsouth
```
- `-n` (`--name`): nome do Resource Group — separado dos RGs de app (`rg-revold-dev` etc.) de propósito, porque o ciclo de vida é diferente: um `terraform destroy` do ambiente de dev nunca deve poder apagar o state.
- `-l` (`--location`): região do Azure onde o recurso é criado — `brazilsouth` pra bater com `var.location` em `iac/terraform/variables.tf` (mesma região de tudo, evita latência cruzada e mantém dado no Brasil por padrão).

```powershell
az storage account create -n revoldtfstate -g rg-revold-tfstate -l brazilsouth --sku Standard_LRS
```
- `-n`: o nome que você validou no primeiro comando.
- `-g` (`--resource-group`): em qual RG esse storage account entra — o que acabou de ser criado.
- `--sku Standard_LRS`: nível de redundância — *Locally Redundant Storage*, 3 cópias dentro do mesmo datacenter. É o mais barato; suficiente pro tfstate (se perder, dá pra reconstruir reimportando os recursos reais — não é dado de cliente). Trocar por `Standard_GRS` (georedundante, outro datacenter) se quiser mais segurança, por um custo um pouco maior.

```powershell
az storage container create -n tfstate --account-name revoldtfstate --auth-mode login
```
- `-n`: nome do **container** (como uma "pasta" dentro do storage account) — precisa bater com `container_name` no bloco `backend` do Passo 6.2.
- `--account-name`: em qual storage account esse container vive.
- `--auth-mode login`: usa a sua própria identidade do Entra ID (já logada via `az login`) pra criar o container, em vez de precisar buscar a account key manualmente — mais simples quando quem está rodando já é `Owner`/`Contributor` do storage account.

### 6.2 — Apontar o Terraform pro backend remoto

Em `iac/terraform/providers.tf`, descomente o bloco já preparado (hoje linhas 13-18) e confirme que os valores batem com o que você acabou de criar:

```hcl
backend "azurerm" {
  resource_group_name  = "rg-revold-tfstate"
  storage_account_name = "revoldtfstate"
  container_name       = "tfstate"
  key                  = "revold.tfstate"
}
```
- `key` é só o nome do arquivo de state *dentro* do container — pode ter mais de um `key` diferente no mesmo container se um dia quiser mais de um state (ex.: um por ambiente), mas começar com um único arquivo é suficiente agora.

```powershell
terraform -chdir=iac/terraform init -migrate-state
```
- `-chdir=iac/terraform`: roda o comando como se você tivesse entrado nessa pasta, sem precisar sair de onde está.
- `init`: baixa o provider `azurerm` e conecta ao backend configurado.
- `-migrate-state`: como já existia um state local (de qualquer teste anterior) e agora tem um backend novo, essa flag pergunta (responda `yes`) se quer copiar o conteúdo do state local pro blob que acabou de ser criado, em vez de começar do zero.

### 6.3 — Loop de teste seguro, sempre lendo antes de aplicar

```powershell
terraform -chdir=iac/terraform fmt -check
```
- Verifica se os arquivos `.tf` seguem a formatação padrão do Terraform (indentação, alinhamento). `-check` só **reporta** o que está fora do padrão (lista os arquivos, sai com código de erro) sem alterar nada — tirar o `-check` faz ele corrigir os arquivos direto.

```powershell
terraform -chdir=iac/terraform validate
```
- Confere se o código é sintaticamente válido e internamente consistente (tipo de variável certo, argumento obrigatório presente) — **não** fala com o Azure, não precisa nem de `az login` pra esse passo específico. Pega erro de digitação antes de gastar tempo com um `plan`.

```powershell
$env:TF_VAR_postgres_admin_password = "escolha-uma-senha-forte-aqui"
terraform -chdir=iac/terraform plan
```
- `$env:TF_VAR_postgres_admin_password = "..."`: `postgres_admin_password` (`iac/terraform/variables.tf`) é `sensitive` e não tem valor padrão de propósito — o comentário no próprio arquivo já avisa "passar via `TF_VAR_postgres_admin_password`, nunca commitar". Terraform lê automaticamente qualquer variável de ambiente no formato `TF_VAR_<nome_da_variável>`. Isso só vale pra essa janela do PowerShell — feche e abra outra, precisa setar de novo (de propósito: não fica salvo em lugar nenhum do disco).
- `plan` (sem `-var-file`): como as outras variáveis (`project_name`, `environment`, `location`) já têm valor padrão em `variables.tf`, só a senha precisa ser passada. `plan` faz um **dry-run** de verdade: conecta no Azure (usa a sessão do `az login`), compara o que o código pede com o que já existe (via o state remoto) e imprime um resumo tipo `Plan: 8 to add, 0 to change, 0 to destroy` — com `+` (cria), `~` (atualiza sem recriar), `-` (destrói) e `-/+` (destrói e recria) na frente de cada recurso. **Leia essa lista inteira antes de aplicar** — é o jeito de pegar "isso vai apagar o banco de produção" antes de acontecer, não depois.

Teste sempre contra `rg-revold-dev` primeiro (o `environment` default em `variables.tf` já é `dev`). Só depois de ver um `plan` limpo rode `terraform -chdir=iac/terraform apply` (ele repete o mesmo plano e pede confirmação digitando `yes`) — e nunca `apply` direto em produção fora do pipeline do Passo 5.

### 6.4 — Automatizar a verificação

- **Lint/segurança estática**, antes de confiar só na leitura manual do plan: `tflint` (sintaxe/boas práticas do provider) e `checkov` ou `tfsec` (regras de segurança — é esse tipo de ferramenta que pega "Key Vault sem `network_acls`", ver Passo 7).
- Adicionar um job em `.github/workflows/ci.yml` que roda `fmt`/`validate`/`plan` em PRs que tocam `iac/**`, sem `apply` — pega erro antes do merge, sem exigir que cada dev lembre de rodar isso localmente toda vez.

## Passo 7 — Segurança e rede

1. **Microsoft Defender for Cloud** → Environment settings → subscription → ativar o plano **Foundational CSPM** (gratuito). Avaliar os planos pagos de Key Vault e Databases, dado que ambos guardam dado de cliente (LGPD, ver `docs/security/README.md`).
2. **Gap atual do Key Vault**: `iac/terraform/modules/key-vault/main.tf` não define `network_acls` — hoje está publicamente acessível, protegido só por RBAC. Adicionar `network_acls { default_action = "Deny", virtual_network_subnet_ids = [...] }` ou um Private Endpoint.
3. **NSGs**: nenhuma subnet em `iac/terraform/modules/network/main.tf` tem Network Security Group hoje. Adicionar um `azurerm_network_security_group` associado à subnet de Container Apps, liberando só o necessário.
4. **Azure Policy** (opcional, alto valor com mais de um dev): atribuir iniciativas built-in tipo "Deny public network access" nos Resource Groups de produção.

## Passo 8 — Notificações

Duas coisas distintas:

- **Alertas operacionais do Azure** (budget, Defender, falha de deploy): Portal → **Azure Monitor** → **Alerts** → **Action groups** → **Create** → adicione uma ação do tipo **Email/SMS/Push/Voice** com seu e-mail. Depois, no Budget do Passo 2 e nas notificações do Defender for Cloud (Environment settings → Email notifications), aponte pra esse mesmo Action Group — assim um lugar só concentra pra onde todo alerta vai.
- **Canal de notificação do produto** (avisar a Nick por e-mail/WhatsApp): já decidido no código, não é item de infra — ver ADR-0018 (SMTP) e ADR-0025 (WhatsApp Business). Ativar é configuração de variável de ambiente (`NOTIFICATION_PROVIDER=smtp`), não trabalho no Portal.

## Checklist adicional

- **Conta de emergência ("break-glass")**: uma terceira conta Global Admin, excluída de MFA condicional, credencial guardada offline — sem isso, perder 2FA da conta do dia a dia trava o acesso ao próprio tenant.
- **Resource Lock** (`CanNotDelete`) em `rg-revold-production` — evita `terraform destroy` ou clique errado apagando produção.
- **Tags obrigatórias** (`environment`, `owner`, `cost-center`) via Azure Policy, pra cost allocation legível no Cost Management.
- **Backup/DR do Postgres**: confirmar retenção e necessidade de geo-redundância — hoje não parametrizado em `iac/terraform/modules/postgres/main.tf`.
- **Retenção de audit log do Entra ID**: no tier Free, sign-in/audit logs ficam ~7–30 dias. Exportar para o Log Analytics workspace que `iac/terraform/modules/container-apps/main.tf` já cria, se LGPD/ISO 27001 (`docs/security/README.md`) for meta real.
- **Secret scanning / Dependabot** no GitHub (Settings → Code security).
- **DPIA/LGPD formal**: já listado como pendente em `docs/security/README.md` — falta dono e data.
- **CNPJ e domínio próprio**: billing em nome de pessoa jurídica (não cartão pessoal) e domínio verificado no Entra ID, para login `@suaempresa.com.br` em vez de `.onmicrosoft.com`.
