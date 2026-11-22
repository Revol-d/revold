output "api_gateway_url" {
  value = module.container_apps.api_gateway_fqdn
}

output "azure_sql_fqdn" {
  value = module.azure_sql.server_fqdn
}

output "key_vault_uri" {
  value = module.key_vault.key_vault_uri
}

output "azure_openai_endpoint" {
  value = module.azure_openai.endpoint
}
