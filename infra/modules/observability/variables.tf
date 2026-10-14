variable "aks_cluster_id" {
  description = "Resource ID of the AKS managed cluster. Used to associate the Prometheus DCR with the cluster."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group that contains all observability resources."
  type        = string
}

variable "location" {
  description = "Azure region for all observability resources."
  type        = string
}

variable "amw_name" {
  description = "Name of the Azure Monitor Workspace (managed Prometheus)."
  type        = string
}

variable "grafana_name" {
  description = "Name of the Azure Managed Grafana instance."
  type        = string
}

variable "grafana_major_version" {
  description = "Grafana major version. Must match a version supported by Azure Managed Grafana. Grafana 11 was retired June 2026; use 12 or later."
  type        = string
  default     = "12"
}

variable "tags" {
  description = "Tags applied to all observability resources."
  type        = map(string)
  default     = {}
}
