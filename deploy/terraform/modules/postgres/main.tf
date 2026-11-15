resource "azurerm_postgresql_flexible_server" "this" {
  name                   = "psql-${var.project_name}-${var.environment}"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "16"
  delegated_subnet_id    = var.postgres_subnet_id
  administrator_login    = "revold_admin"
  administrator_password = var.admin_password
  storage_mb             = 32768
  sku_name               = "B_Standard_B1ms" # menor SKU — adequado para MVP de um cliente (ADR-0004)
  zone                   = "1"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "revold"
  server_id = azurerm_postgresql_flexible_server.this.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# pgvector (core-ai-assistant, ADR-0006) precisa da extensão habilitada via
# parâmetro do servidor, não só CREATE EXTENSION dentro do banco.
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "VECTOR"
}
