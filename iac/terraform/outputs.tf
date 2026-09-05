output "api_gateway_url" {
  value = module.container_apps.api_gateway_fqdn
}

output "postgres_fqdn" {
  value = module.postgres.server_fqdn
}

output "key_vault_uri" {
  value = module.key_vault.key_vault_uri
}

output "azure_openai_endpoint" {
  value = module.azure_openai.endpoint
}
