# Guia de Infraestrutura — Configuração do Azure

Este guia cobre a configuração de **identidade, governança, billing e segurança** no Portal do Azure para o time (hoje duas pessoas: uma focada em infra, outra em análise/refatoração do código). Ele complementa, mas não substitui, ADR-0004 (plataforma de execução) e ADR-0008 (CI/CD) — a regra de lá continua valendo: **nenhum recurso de workload é criado manualmente pelo Portal**, tudo via Terraform (`iac/terraform/`). O Portal entra só para o que não é modelável como recurso de app: usuários, billing, policy, Defender.

## Conceitos — antes de abrir o Portal

| Termo | O que é | Uso aqui |
|---|---|---|
| **Tenant (Entra ID)** | Diretório de identidade | Separa *organizações*. Não precisa de tenant novo pra separar dev/hml/prod — isso é Resource Group. |
| **Subscription** | Unidade de billing + boundary de política/RBAC | Opcional pra isolamento mais forte entre ambientes; não necessário no estágio atual. |
| **Resource Group** | Agrupamento de recursos dentro de uma subscription | É o que `iac/terraform/modules/network/main.tf` já usa (`rg-${project_name}-${environment}`). |
| **Role RBAC** (Contributor, Owner) | Permissão pra *gerenciar recursos* | O que o segundo dev precisa pra criar/gerenciar recursos de dev. |
| **Role de Billing** (Billing Reader, Account Owner) | Permissão pra *ver/gerenciar custo e pagamento* | Separado do RBAC — Contributor não implica acesso a billing, mas em várias contas o custo fica visível por padrão a menos que isso seja desligado explicitamente (Passo 2). |
| **Login Entra ID vs. e-mail real** | Entra ID dá uma *conta* (`pessoa@dominio.onmicrosoft.com`), não uma caixa que recebe mensagem | Suficiente pra acesso ao Portal/CLI. E-mail que recebe mensagem de verdade é Microsoft 365/Google Workspace — serviço separado, pago, exige domínio próprio. |

## Passo 1 — Identidade (Entra ID)

Não é necessário criar um tenant novo — o tenant atual já existe (criado junto com a primeira subscription). Criar um tenant extra é gratuito (Entra ID Free), mas resolve um problema diferente (isolar identidade de outra organização, não separar ambientes de um mesmo projeto).

1. Portal → **Microsoft Entra ID** → **Users** → **New user** → **Create new user** (não "Invite external user" — Member, não Guest, para o segundo dev poder ser dono de recursos sem restrição de guest).
2. Nome de usuário: `pessoa@dominio.onmicrosoft.com` (domínio padrão grátis) ou domínio próprio verificado, se houver.
3. Não atribuir nenhuma role de diretório alta (Global Admin) à conta nova.
4. Ativar MFA para as duas contas: **Microsoft Entra ID → Properties → Manage security defaults → Enable** (MFA obrigatório pra todo o tenant, grátis, sem precisar de Conditional Access P1/P2).

## Passo 2 — Isolar billing

RBAC e billing são sistemas separados — "ele só tem Contributor" não é suficiente por padrão em várias contas.

1. Portal → **Cost Management + Billing** → selecione a **Billing Account** → **Policies** (nome exato varia conforme o tipo de contrato — *Microsoft Customer Agreement* é o mais comum em conta nova paga por cartão).
2. Desative a opção equivalente a **"Azure RBAC access to cost management data"**. Com isso desligado, só quem tem role de billing explícita vê custo — Contributor/Owner em recurso não basta.
3. Garantir que a conta do segundo dev não recebe nenhuma role em **Access control (IAM)** no nível da Billing Account/Billing Profile — só nas subscriptions/resource groups (Passo 4).
4. Configurar um **Budget** (Cost Management → Budgets) com Action Group (Passo 8) pra alerta antes de qualquer surpresa de fatura.

## Passo 3 — Separação de ambientes

Recomendado para o estágio atual (2 pessoas, 1 cliente): **uma subscription**, com os três Resource Groups que o Terraform já cria (`rg-revold-dev`, `rg-revold-staging`, `rg-revold-production` — ver `var.environment` em `iac/terraform/variables.tf`). Ter mais Resource Groups não tem custo.

Se no futuro for necessário isolamento mais forte (cota separada, política diferente por ambiente), criar uma segunda subscription (`revold-nonprod` / `revold-prod`) no mesmo tenant — criar subscription é grátis, só os recursos usados são cobrados. Não é necessário decidir isso agora.

## Passo 4 — RBAC

- **Conta admin** (infra): `Owner` ou `Contributor` + `User Access Administrator` no nível da subscription — é essa identidade (via pipeline, não localmente) que aplica Terraform contra produção.
- **Conta do segundo dev**: role **Contributor** (built-in) atribuída só nos Resource Groups `rg-revold-dev` (e `staging`, se também responsável por homologação) — nunca em `rg-revold-production` nem na subscription inteira.
  - Portal → Resource Group `rg-revold-dev` → **Access control (IAM)** → **Add role assignment** → `Contributor` → usuário.

## Passo 5 — Pipeline dev → hml → prod (OIDC)

ADR-0008 já decidiu deploy via GitHub Actions com OIDC (sem secret de longa duração) — falta implementar o workflow.

1. Criar três **App Registrations** (Entra ID → App registrations → New registration): `sp-revold-dev`, `sp-revold-staging`, `sp-revold-prod`.
2. Em cada uma → **Certificates & secrets → Federated credentials → Add credential** → cenário **GitHub Actions deploying Azure resources**: organização/repo = este repositório; Entity type **Environment**; nome igual ao GitHub Environment (`dev`/`staging`/`production`).
3. Dar **Contributor** no Resource Group correspondente a cada service principal (mesmo fluxo do Passo 4, atribuindo ao app registration em vez de usuário).
4. GitHub → **Settings → Environments** → criar `dev`, `staging`, `production`. Em `production`, configurar **required reviewers** (aprovação manual antes do apply rodar).
5. Criar `.github/workflows/cd.yml` (ainda não existe — hoje `ci.yml` só testa) usando `azure/login@v2` com `client-id`/`tenant-id`/`subscription-id` (OIDC, sem `client-secret`), rodando `terraform plan` em PR e `terraform apply` só após merge, por ambiente.

## Passo 6 — Testar o Terraform na prática

O backend remoto está comentado em `iac/terraform/providers.tf` — sem ele, duas pessoas aplicando Terraform correm o risco de sobrescrever o state uma da outra.

1. **Bootstrap manual único** (única exceção justificável a "nunca pelo Portal/CLI direto" — o storage account do state não pode depender do próprio Terraform):
   ```
   az group create -n rg-revold-tfstate -l brazilsouth
   az storage account create -n revoldtfstate -g rg-revold-tfstate --sku Standard_LRS
   az storage container create -n tfstate --account-name revoldtfstate
   ```
2. Descomentar o bloco `backend "azurerm"` em `providers.tf` e rodar `terraform init -migrate-state`.
3. Loop de teste seguro, sempre lendo o `plan` antes de aplicar:
   ```
   az login
   terraform -chdir=iac/terraform fmt -check
   terraform -chdir=iac/terraform validate
   terraform -chdir=iac/terraform plan -var-file=dev.tfvars
   ```
   Testar primeiro só contra `rg-revold-dev`; nunca `apply` direto em produção fora do pipeline do Passo 5.
4. Lint/segurança estática antes de confiar na leitura manual: `tflint` (sintaxe/boas práticas) e `checkov` ou `tfsec` (detecta coisas como Key Vault sem `network_acls` — ver Passo 7).
5. Adicionar um job em `.github/workflows/ci.yml` que roda `fmt`/`validate`/`plan` em PRs que tocam `iac/**`, sem apply — pega erro antes do merge.

## Passo 7 — Segurança e rede

1. **Microsoft Defender for Cloud** → Environment settings → subscription → ativar o plano **Foundational CSPM** (gratuito). Avaliar os planos pagos de Key Vault e Databases, dado que ambos guardam dado de cliente (LGPD, ver `docs/security/README.md`).
2. **Gap atual do Key Vault**: `iac/terraform/modules/key-vault/main.tf` não define `network_acls` — hoje está publicamente acessível, protegido só por RBAC. Adicionar `network_acls { default_action = "Deny", virtual_network_subnet_ids = [...] }` ou um Private Endpoint.
3. **NSGs**: nenhuma subnet em `iac/terraform/modules/network/main.tf` tem Network Security Group hoje. Adicionar um `azurerm_network_security_group` associado à subnet de Container Apps, liberando só o necessário.
4. **Azure Policy** (opcional, alto valor com mais de um dev): atribuir iniciativas built-in tipo "Deny public network access" nos Resource Groups de produção.

## Passo 8 — Notificações

Duas coisas distintas:

- **Alertas operacionais do Azure** (budget, Defender, falha de deploy): **Azure Monitor → Alerts → Action Groups**, ligado a um Budget (Passo 2) e aos alertas do Defender for Cloud (Environment settings → Email notifications).
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
