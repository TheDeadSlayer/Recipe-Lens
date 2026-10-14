variable "project" {
  description = "Project name used for resource naming."
  type        = string
  default     = "recipelens"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Primary Azure region."
  type        = string
  default     = "canadacentral"
}

variable "suffix" {
  description = "Stable suffix used for globally unique Azure resource names."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{4,6}$", var.suffix))
    error_message = "suffix must contain 4-6 lowercase letters or numbers."
  }
}

variable "vnet_address_space" {
  description = "Address space for the development Virtual Network."
  type        = list(string)
  default     = ["10.20.0.0/16"]
}

variable "aks_subnet_prefixes" {
  description = "CIDR prefixes for the AKS subnet."
  type        = list(string)
  default     = ["10.20.0.0/20"]
}

variable "postgres_subnet_prefixes" {
  description = "CIDR prefixes for the PostgreSQL subnet."
  type        = list(string)
  default     = ["10.20.16.0/24"]
}

# ---------------------------------------------------------------------------
# AKS
# ---------------------------------------------------------------------------

variable "kubernetes_version" {
  description = "Kubernetes version for the AKS cluster and system node pool."
  type        = string
  default     = "1.36"
}

variable "node_vm_size" {
  description = "VM SKU for the AKS system node pool."
  type        = string
  default     = "Standard_D2pds_v5"
}

variable "node_count" {
  description = "Initial node count for the AKS system node pool."
  type        = number
  default     = 1
}

variable "pod_cidr" {
  description = "CIDR for pod overlay networking (CNI Overlay). Must not overlap with VNet or service_cidr."
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_cidr" {
  description = "CIDR for Kubernetes services. Must not overlap with VNet or pod_cidr."
  type        = string
  default     = "10.30.0.0/16"
}

variable "dns_service_ip" {
  description = "IP address for the Kubernetes DNS service. Must be within service_cidr."
  type        = string
  default     = "10.30.0.10"
}

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

variable "pg_administrator_login" {
  description = "PostgreSQL administrator username."
  type        = string
  default     = "recipelensadmin"
}

variable "pg_administrator_password" {
  description = "PostgreSQL administrator password. Supply via TF_VAR_pg_administrator_password env var or a gitignored terraform.tfvars file. Never commit this value. Passed only into the write-only attribute — never stored in Terraform state."
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "pg_administrator_password_version" {
  description = "Increment to trigger a password rotation. Passed to administrator_password_wo_version; Terraform re-sends the password to Azure only when this number increases. Do not change it unless intentionally rotating the password."
  type        = number
  default     = 1
}

variable "postgresql_version" {
  description = "PostgreSQL major version. 17 is deliberately selected as a mature, fully supported GA release. Azure also supports 18 (newest) and 16 (previous LTS)."
  type        = string
  default     = "17"
}

variable "pg_sku_name" {
  description = "PostgreSQL Flexible Server SKU. AzureRM format: <TierPrefix>_<VMSku>. B_Standard_B1ms = Burstable 1 vCPU / 2 GB RAM."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "pg_storage_mb" {
  description = "PostgreSQL storage in MB. Minimum supported is 32768 (32 GB)."
  type        = number
  default     = 32768
}

variable "pg_backup_retention_days" {
  description = "PostgreSQL backup retention in days."
  type        = number
  default     = 7
}

variable "pg_database_name" {
  description = "Name of the application database to create on the server."
  type        = string
  default     = "recipelens"
}
