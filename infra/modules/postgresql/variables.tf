variable "server_name" {
  description = "Name of the PostgreSQL Flexible Server. Must be globally unique, 3-63 chars, lowercase letters/numbers/hyphens."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group containing the PostgreSQL server."
  type        = string
}

variable "location" {
  description = "Azure region for the PostgreSQL server."
  type        = string
}

variable "delegated_subnet_id" {
  description = "Resource ID of the subnet delegated to Microsoft.DBforPostgreSQL/flexibleServers."
  type        = string
}

variable "virtual_network_id" {
  description = "Resource ID of the VNet. Used to link the private DNS zone."
  type        = string
}

variable "administrator_login" {
  description = "PostgreSQL administrator username."
  type        = string
  default     = "recipelensadmin"
}

variable "administrator_password" {
  description = "PostgreSQL administrator password. Supply at apply time via TF_VAR_administrator_password env var or a gitignored tfvars file. Never stored in Terraform state (passed only into write-only attribute administrator_password_wo)."
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "administrator_password_version" {
  description = "Monotonically increasing integer that triggers a password rotation on the server when incremented. Increment this value deliberately when rotating the administrator password — do not change it otherwise, as it will cause Terraform to re-send the password to Azure even if the value itself has not changed."
  type        = number
  default     = 1
}

variable "postgresql_version" {
  description = "PostgreSQL major version. 17 is deliberately selected as a mature, fully supported GA release. Azure also supports 18 (newest) and 16 (previous LTS)."
  type        = string
  default     = "17"
}

variable "sku_name" {
  description = "PostgreSQL Flexible Server SKU. AzureRM format: <TierPrefix>_<VMSku> e.g. B_Standard_B1ms (Burstable, 1 vCPU / 2 GB RAM, cheapest dev SKU in Canada Central). Tier prefixes: B=Burstable, GP=GeneralPurpose, MO=MemoryOptimized."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "storage_mb" {
  description = "Storage size in MB. 32768 (32 GB) is the minimum supported."
  type        = number
  default     = 32768
}

variable "backup_retention_days" {
  description = "Backup retention in days."
  type        = number
  default     = 7
}

variable "database_name" {
  description = "Name of the PostgreSQL database to create."
  type        = string
  default     = "recipelens"
}

variable "tags" {
  description = "Tags applied to all PostgreSQL resources."
  type        = map(string)
  default     = {}
}
