data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "this" {
  name                = "kv-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Acesso via Azure RBAC (não policy legada) — permissão concedida por
  # azurerm_role_assignment na identidade gerenciada dos serviços, não por
  # segredo distribuído (ver ADR-0003).
  enable_rbac_authorization = true
}

resource "azurerm_user_assigned_identity" "workload" {
  name                = "id-${var.project_name}-${var.environment}-workload"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "workload_secrets_user" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.workload.principal_id
}
