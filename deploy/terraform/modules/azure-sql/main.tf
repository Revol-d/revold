# Azure SQL Database (PaaS), não Managed Instance nem VM -- substitui o módulo
# `postgres` (Fase 7 do plano de migração Postgres -> Azure SQL, docs internos:
# corte concluído). Free tier confirmado disponível em Nov/2026 (100.000
# vCore-segundos + 32GB/mês por banco, até 10 bancos grátis por subscription,
# serverless com auto-pause) -- mesmo SKU validado nos spikes manuais desta
# migração (az sql db create --use-free-limit --free-limit-exhaustion-behavior
# AutoPause).
#
# Sem VNet/subnet dedicada (diferente do Postgres Flexible Server, que exigia
# subnet delegada): Azure SQL Database como PaaS público usa firewall de IP, não
# integração de rede -- adequado ao MVP de um cliente só (mesmo racional do SKU
# pequeno do Postgres que este módulo substitui).
resource "azurerm_mssql_server" "this" {
  name                         = "sql-${var.project_name}-${var.environment}"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  version                      = "12.0"
  administrator_login          = "revold_admin"
  administrator_login_password = var.admin_password
  minimum_tls_version          = "1.2"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_mssql_database" "app" {
  name      = "revold"
  server_id = azurerm_mssql_server.this.id
  collation = "Latin1_General_100_CI_AS_SC_UTF8"

  # Serverless Gen5, 2 vCores -- o mesmo SKU usado pelo free tier via
  # `az sql db create --use-free-limit --free-limit-exhaustion-behavior
  # AutoPause` (confirmado nos spikes manuais desta migração). O provider
  # azurerm ~> 3.116 (checado: v3.117.1) AINDA NÃO expõe `use_free_limit`/
  # `free_limit_exhaustion_behavior` no `azurerm_mssql_database` -- terraform
  # validate reprova com "argument not expected". Até o provider alcançar o
  # recurso, o limite gratuito precisa ser ativado manualmente uma vez (Portal
  # ou `az sql db update --use-free-limit --free-limit-exhaustion-behavior
  # AutoPause`) depois do primeiro `terraform apply`; o Terraform não vai
  # desfazer isso num `apply` seguinte (o atributo não está no state).
  sku_name                    = "GP_S_Gen5_2"
  min_capacity                = 0.5
  auto_pause_delay_in_minutes = 60

  lifecycle {
    prevent_destroy = true
  }
}

# Regra especial do Azure (0.0.0.0-0.0.0.0): libera outros serviços Azure (os
# Container Apps deste projeto, ADR-0004), não a internet pública -- a conexão
# ainda exige usuário/senha (ou Azure AD) normalmente.
resource "azurerm_mssql_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}
