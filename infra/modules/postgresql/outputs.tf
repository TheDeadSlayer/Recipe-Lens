output "postgresql_server_id" {
  description = "Resource ID of the PostgreSQL Flexible Server."
  value       = azurerm_postgresql_flexible_server.this.id
}

output "postgresql_server_name" {
  description = "Name of the PostgreSQL Flexible Server."
  value       = azurerm_postgresql_flexible_server.this.name
}

output "postgresql_fqdn" {
  description = "Fully-qualified domain name of the PostgreSQL Flexible Server."
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "postgresql_database_name" {
  description = "Name of the application database."
  value       = azurerm_postgresql_flexible_server_database.app.name
}

output "private_dns_zone_id" {
  description = "Resource ID of the private DNS zone used for PostgreSQL VNet integration."
  value       = azurerm_private_dns_zone.postgres.id
}

output "private_dns_zone_name" {
  description = "Name of the private DNS zone."
  value       = azurerm_private_dns_zone.postgres.name
}
