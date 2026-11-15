output "api_gateway_fqdn" { value = azurerm_container_app.api_gateway.ingress[0].fqdn }
