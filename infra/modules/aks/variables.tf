variable "name" {
  description = "Name of the AKS cluster."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group containing the AKS cluster."
  type        = string
}

variable "location" {
  description = "Azure region for the AKS cluster."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for the cluster and system node pool."
  type        = string
}

variable "aks_subnet_id" {
  description = "Resource ID of the subnet for AKS nodes."
  type        = string
}

variable "acr_id" {
  description = "Resource ID of the Azure Container Registry to grant AcrPull on."
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of the Log Analytics Workspace for AKS OMS agent."
  type        = string
}

variable "node_vm_size" {
  description = "VM SKU for the system node pool."
  type        = string
  default     = "Standard_D2pds_v5"
}

variable "node_count" {
  description = "Initial node count for the system node pool."
  type        = number
  default     = 1
}

variable "pod_cidr" {
  description = "CIDR for pod overlay networking (CNI Overlay)."
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_cidr" {
  description = "CIDR for Kubernetes services."
  type        = string
  default     = "10.30.0.0/16"
}

variable "dns_service_ip" {
  description = "IP address for the Kubernetes DNS service. Must be within service_cidr."
  type        = string
  default     = "10.30.0.10"
}

variable "managed_prometheus_enabled" {
  description = "Enable the AKS managed Prometheus metrics add-on. When true, Azure creates a platform-managed DCR and DCE in a MA_<workspace>_<location>_managed resource group. Pair with an explicit DCR/DCRA in the observability module to route metrics to a custom Azure Monitor Workspace."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Key Vault Secrets Store CSI add-on
# ---------------------------------------------------------------------------

variable "key_vault_csi_enabled" {
  description = "Enable the Azure Key Vault Secrets Store CSI provider add-on. When true, the CSI driver is installed on every node and can mount Key Vault secrets as volumes."
  type        = bool
  default     = false
}

variable "key_vault_csi_rotation_interval" {
  description = "Polling interval for the CSI driver secret rotation. Only used when key_vault_csi_enabled = true. Use Go duration syntax (e.g. '2m', '1h'). A short interval (2m) is reasonable for dev; use a longer interval in production to reduce Key Vault API calls."
  type        = string
  default     = "2m"
}

variable "tags" {
  description = "Tags applied to all AKS resources."
  type        = map(string)
  default     = {}
}
