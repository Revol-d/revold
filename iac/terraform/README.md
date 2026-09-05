# IaC — Terraform (Azure)

Skeleton criado seguindo ADR-0004 (Container Apps, não AKS). **Ainda não foi aplicado** — não há credencial Azure disponível no ambiente onde isto foi escrito. Antes do primeiro `terraform apply`:

1. `az login` (ou service principal via variáveis `ARM_*` para uso em CI).
2. Criar (manualmente, uma única vez) uma storage account para o state remoto e descomentar o bloco `backend "azurerm"` em `providers.tf` — só essa parte nasce fora do Terraform, por definição.
3. `export TF_VAR_postgres_admin_password="..."` (nunca commitar a senha).
4. `terraform init && terraform plan`.

## Módulos
- `modules/network` — resource group, VNet, subnets (uma delegada para Postgres Flexible Server).
- `modules/key-vault` — Key Vault com autorização via Azure RBAC + identidade gerenciada (`azurerm_user_assigned_identity`) que os Container Apps usam para ler segredos sem credencial distribuída (ADR-0003).
- `modules/postgres` — Postgres Flexible Server com a extensão `VECTOR` habilitada (pgvector, para o RAG do `core-ai-assistant`, ADR-0006). SKU pequeno (`B_Standard_B1ms`), adequado ao volume de um único cliente piloto.
- `modules/container-apps` — Container Apps Environment + o primeiro Container App (`api-gateway`), com `min_replicas = 0` (escala a zero em ausência de tráfego).

## Não incluído ainda (deliberado)
- Deploy real da imagem do `api-gateway` (hoje aponta para uma imagem placeholder da Microsoft) — entra quando o workflow de CI publicar a imagem real.
- `admin-dashboard` e `storefront` como Container Apps — o storefront (Next.js) provavelmente é melhor servido por Azure Static Web Apps ou Vercel do que por um Container App; decisão a ser tomada em ADR próprio quando chegar a hora do deploy do frontend.
- Migração para AKS (ver ADR-0004) — sem módulo ainda, só a decisão registrada.
