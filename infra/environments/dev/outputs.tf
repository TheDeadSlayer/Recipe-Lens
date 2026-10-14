output "resource_group_name" {
  description = "Development Resource Group name."
  value       = module.resource_group.name
}

output "resource_group_id" {
  description = "Development Resource Group ID."
  value       = module.resource_group.id
}

output "vnet_name" {
  description = "Development Virtual Network name."
  value       = module.networking.vnet_name
}

output "vnet_id" {
  description = "Development Virtual Network resource ID."
  value       = module.networking.vnet_id
}

output "aks_subnet_id" {
  description = "AKS subnet resource ID."
  value       = module.networking.aks_subnet_id
}

output "postgres_subnet_id" {
  description = "PostgreSQL subnet resource ID."
  value       = module.networking.postgres_subnet_id
}

# ---------------------------------------------------------------------------
# ACR
# ---------------------------------------------------------------------------

output "acr_name" {
  description = "Azure Container Registry name."
  value       = module.acr.name
}

output "acr_login_server" {
  description = "ACR login server hostname."
  value       = module.acr.login_server
}

output "acr_id" {
  description = "ACR resource ID."
  value       = module.acr.id
}

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

output "law_name" {
  description = "Log Analytics Workspace name."
  value       = module.monitoring.name
}

output "law_id" {
  description = "Log Analytics Workspace resource ID."
  value       = module.monitoring.id
}

output "law_workspace_id" {
  description = "Log Analytics Workspace GUID (used by AKS diagnostics)."
  value       = module.monitoring.workspace_id
}

# ---------------------------------------------------------------------------
# AKS
# ---------------------------------------------------------------------------

output "aks_cluster_name" {
  description = "AKS cluster name."
  value       = module.aks.cluster_name
}

output "aks_cluster_id" {
  description = "AKS cluster resource ID."
  value       = module.aks.cluster_id
}

output "aks_node_resource_group" {
  description = "Name of the auto-created AKS node resource group (MC_...)."
  value       = module.aks.node_resource_group
}

output "aks_oidc_issuer_url" {
  description = "OIDC issuer URL for Workload Identity federation."
  value       = module.aks.oidc_issuer_url
}

output "aks_kubelet_identity_object_id" {
  description = "Object ID of the AKS kubelet managed identity (ACR pulls, node-level Azure calls)."
  value       = module.aks.kubelet_identity_object_id
}

output "aks_control_plane_identity_id" {
  description = "Resource ID of the AKS control-plane user-assigned managed identity."
  value       = module.aks.control_plane_identity_id
}

output "aks_control_plane_identity_principal_id" {
  description = "Principal ID of the AKS control-plane UAMI."
  value       = module.aks.control_plane_identity_principal_id
}

# ---------------------------------------------------------------------------
# Observability — Azure Monitor Workspace + Managed Grafana
# ---------------------------------------------------------------------------

output "azure_monitor_workspace_id" {
  description = "Resource ID of the Azure Monitor Workspace (managed Prometheus)."
  value       = module.observability.azure_monitor_workspace_id
}

output "azure_monitor_workspace_name" {
  description = "Name of the Azure Monitor Workspace."
  value       = module.observability.azure_monitor_workspace_name
}

output "grafana_id" {
  description = "Resource ID of the Azure Managed Grafana instance."
  value       = module.observability.grafana_id
}

output "grafana_name" {
  description = "Name of the Azure Managed Grafana instance."
  value       = module.observability.grafana_name
}

output "grafana_endpoint" {
  description = "Public HTTPS endpoint of the Azure Managed Grafana instance."
  value       = module.observability.grafana_endpoint
}

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

output "postgresql_server_name" {
  description = "PostgreSQL Flexible Server name."
  value       = module.postgresql.postgresql_server_name
}

output "postgresql_fqdn" {
  description = "PostgreSQL Flexible Server FQDN (private DNS, VNet-only)."
  value       = module.postgresql.postgresql_fqdn
}

output "postgresql_database_name" {
  description = "Application database name."
  value       = module.postgresql.postgresql_database_name
}

output "postgresql_server_id" {
  description = "PostgreSQL Flexible Server resource ID."
  value       = module.postgresql.postgresql_server_id
}

output "private_dns_zone_id" {
  description = "Resource ID of the PostgreSQL private DNS zone."
  value       = module.postgresql.private_dns_zone_id
}

# ---------------------------------------------------------------------------
# Key Vault
# ---------------------------------------------------------------------------

output "key_vault_id" {
  description = "Resource ID of the Azure Key Vault."
  value       = module.key_vault.key_vault_id
}

output "key_vault_name" {
  description = "Azure Key Vault name."
  value       = module.key_vault.key_vault_name
}

output "key_vault_uri" {
  description = "Azure Key Vault URI (used by the CSI driver SecretProviderClass)."
  value       = module.key_vault.key_vault_uri
}

# ---------------------------------------------------------------------------
# RecipeLens workload identity
# ---------------------------------------------------------------------------

output "workload_identity_id" {
  description = "Resource ID of the RecipeLens workload user-assigned managed identity."
  value       = module.workload_identity.workload_identity_id
}

output "workload_identity_client_id" {
  description = "Client ID of the RecipeLens workload UAMI. Annotate the Kubernetes ServiceAccount with: azure.workload.identity/client-id: <this value>."
  value       = module.workload_identity.workload_identity_client_id
}

output "workload_identity_principal_id" {
  description = "Principal ID (object ID) of the RecipeLens workload UAMI."
  value       = module.workload_identity.workload_identity_principal_id
}

output "workload_identity_federated_credential_id" {
  description = "Resource ID of the federated identity credential (AKS OIDC → workload UAMI binding)."
  value       = module.workload_identity.workload_identity_federated_credential_id
}
