variable "name" {
  description = "Name of the workload user-assigned managed identity (e.g. recipelens-dev-app-identity)."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group in which to create the workload UAMI."
  type        = string
}

variable "location" {
  description = "Azure region for the workload UAMI."
  type        = string
}

variable "federated_credential_name" {
  description = "Name of the federated identity credential resource."
  type        = string
}

variable "oidc_issuer_url" {
  description = "AKS OIDC issuer URL. Used as the token issuer in the federated credential. Sourced from the AKS module output."
  type        = string
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace where the RecipeLens ServiceAccount will live."
  type        = string
  default     = "recipelens"
}

variable "kubernetes_service_account" {
  description = "Name of the Kubernetes ServiceAccount that will be federated with this UAMI."
  type        = string
  default     = "recipelens-backend"
}

variable "key_vault_id" {
  description = "Resource ID of the Azure Key Vault. The workload UAMI is granted Key Vault Secrets User scoped to this vault."
  type        = string
}

variable "tags" {
  description = "Tags applied to all workload identity resources."
  type        = map(string)
  default     = {}
}
