output "id" {
  description = "Log Analytics Workspace resource ID."
  value       = azurerm_log_analytics_workspace.this.id
}

output "name" {
  description = "Log Analytics Workspace name."
  value       = azurerm_log_analytics_workspace.this.name
}

output "workspace_id" {
  description = "Log Analytics Workspace GUID (used by AKS diagnostics)."
  value       = azurerm_log_analytics_workspace.this.workspace_id
}

output "primary_shared_key" {
  description = "Primary shared key for the Log Analytics Workspace."
  value       = azurerm_log_analytics_workspace.this.primary_shared_key
  sensitive   = true
}
