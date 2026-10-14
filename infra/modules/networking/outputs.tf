output "vnet_id" {
  description = "Virtual Network resource ID."
  value       = azurerm_virtual_network.this.id
}

output "vnet_name" {
  description = "Virtual Network name."
  value       = azurerm_virtual_network.this.name
}

output "aks_subnet_id" {
  description = "AKS subnet resource ID."
  value       = azurerm_subnet.aks.id
}

output "postgres_subnet_id" {
  description = "PostgreSQL subnet resource ID."
  value       = azurerm_subnet.postgres.id
}