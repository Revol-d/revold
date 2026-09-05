# Azure OpenAI (core-ai-assistant, ADR-0006/ADR-0011) — um Cognitive
# Services account (kind="OpenAI") com dois deployments: chat (completion)
# e embedding (RAG sobre o catálogo via pgvector).
resource "azurerm_cognitive_account" "openai" {
  name                = "aoai-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "OpenAI"
  sku_name            = "S0"

  # A chave primária vai para o Key Vault (ver azurerm_key_vault_secret
  # abaixo) — nenhum segredo distribuído manualmente. A identidade
  # gerenciada dos serviços (workload identity) também recebe acesso via
  # role assignment, para quando o adapter migrar de API key para
  # autenticação via Azure AD (ver AzureOpenAILLMProvider, ADR-0011).
  public_network_access_enabled = true
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.chat_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.chat_model_name
    version = var.chat_model_version
  }

  sku {
    name     = "Standard"
    capacity = var.chat_capacity
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.embedding_model_name
    version = var.embedding_model_version
  }

  sku {
    name     = "Standard"
    capacity = var.embedding_capacity
  }
}

resource "azurerm_role_assignment" "workload_openai_user" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.workload_identity_principal_id
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "azure-openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = var.key_vault_id
}
