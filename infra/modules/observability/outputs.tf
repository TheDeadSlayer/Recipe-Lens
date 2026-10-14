output "azure_monitor_workspace_id" {
  description = "Resource ID of the Azure Monitor Workspace."
  value       = azurerm_monitor_workspace.this.id
}

output "azure_monitor_workspace_name" {
  description = "Name of the Azure Monitor Workspace."
  value       = azurerm_monitor_workspace.this.name
}

output "azure_monitor_workspace_query_endpoint" {
  description = "Prometheus query endpoint of the Azure Monitor Workspace."
  value       = azurerm_monitor_workspace.this.query_endpoint
}

output "grafana_id" {
  description = "Resource ID of the Azure Managed Grafana instance."
  value       = azurerm_dashboard_grafana.this.id
}

output "grafana_name" {
  description = "Name of the Azure Managed Grafana instance."
  value       = azurerm_dashboard_grafana.this.name
}

output "grafana_endpoint" {
  description = "Public HTTPS endpoint of the Azure Managed Grafana instance."
  value       = azurerm_dashboard_grafana.this.endpoint
}

output "data_collection_endpoint_id" {
  description = "Resource ID of the Prometheus Data Collection Endpoint."
  value       = azurerm_monitor_data_collection_endpoint.prometheus.id
}

output "data_collection_rule_id" {
  description = "Resource ID of the Prometheus Data Collection Rule."
  value       = azurerm_monitor_data_collection_rule.prometheus.id
}

output "grafana_principal_id" {
  description = "Principal ID of the Grafana system-assigned managed identity."
  value       = azurerm_dashboard_grafana.this.identity[0].principal_id
}
