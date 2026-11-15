resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${var.project_name}-${var.environment}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  infrastructure_subnet_id   = var.container_apps_subnet_id
}

resource "azurerm_container_app" "api_gateway" {
  name                         = "ca-${var.project_name}-api-gateway-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.workload_identity_id]
  }

  template {
    container {
      name   = "api-gateway"
      # Substituído pela imagem publicada no build de CI — placeholder até o
      # primeiro workflow de deploy existir.
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
    min_replicas = 0 # escala a zero — adequado para o volume de um cliente no MVP
    max_replicas = 3
  }

  secret {
    name  = "database-url"
    value = var.database_url_placeholder
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
