output "cluster_id" {
  description = "AKS cluster resource ID."
  value       = azurerm_kubernetes_cluster.this.id
}

output "cluster_name" {
  description = "AKS cluster name."
  value       = azurerm_kubernetes_cluster.this.name
}

output "node_resource_group" {
  description = "Name of the auto-created node resource group (MC_...)."
  value       = azurerm_kubernetes_cluster.this.node_resource_group
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL for Workload Identity federation."
  value       = azurerm_kubernetes_cluster.this.oidc_issuer_url
}

output "kubelet_identity_object_id" {
  description = "Object ID of the AKS-managed kubelet identity (shared across the node pool). Used for ACR image pulls and kubelet Azure API calls. Not the Workload Identity — that is federated per-Pod via OIDC + ServiceAccount."
  value       = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
}

output "control_plane_identity_id" {
  description = "Resource ID of the AKS control-plane user-assigned managed identity."
  value       = azurerm_user_assigned_identity.aks_control_plane.id
}

output "control_plane_identity_principal_id" {
  description = "Principal ID of the AKS control-plane UAMI (subnet/NIC/LB operations)."
  value       = azurerm_user_assigned_identity.aks_control_plane.principal_id
}

output "key_vault_csi_secret_identity" {
  description = "Azure-managed identity auto-created for the Key Vault CSI add-on in the node resource group (MC_...). This is NOT the RecipeLens workload identity — it is used by the CSI driver agent itself. Exposed for observability only."
  value       = azurerm_kubernetes_cluster.this.key_vault_secrets_provider[*].secret_identity
}
