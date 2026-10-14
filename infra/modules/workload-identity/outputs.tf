output "workload_identity_id" {
  description = "Resource ID of the RecipeLens workload user-assigned managed identity."
  value       = azurerm_user_assigned_identity.workload.id
}

output "workload_identity_client_id" {
  description = "Client ID of the RecipeLens workload UAMI. Used in the Kubernetes ServiceAccount annotation: azure.workload.identity/client-id."
  value       = azurerm_user_assigned_identity.workload.client_id
}

output "workload_identity_principal_id" {
  description = "Principal ID (object ID) of the RecipeLens workload UAMI. Used for additional role assignments."
  value       = azurerm_user_assigned_identity.workload.principal_id
}

output "workload_identity_federated_credential_id" {
  description = "Resource ID of the federated identity credential binding the Kubernetes ServiceAccount to the workload UAMI."
  value       = azurerm_federated_identity_credential.workload.id
}
