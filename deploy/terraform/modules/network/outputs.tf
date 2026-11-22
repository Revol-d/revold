output "resource_group_name" { value = azurerm_resource_group.this.name }
output "location" { value = azurerm_resource_group.this.location }
output "container_apps_subnet_id" { value = azurerm_subnet.container_apps.id }
output "vnet_id" { value = azurerm_virtual_network.this.id }
