variable "name" {
  description = "Name of the Azure Key Vault. Must be 3-24 characters, alphanumeric and hyphens only, globally unique."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.name))
    error_message = "Key Vault name must be 3-24 characters, start with a letter, end with a letter or digit, and contain only letters, digits, and hyphens."
  }
}

variable "resource_group_name" {
  description = "Resource Group in which to create the Key Vault."
  type        = string
}

variable "location" {
  description = "Azure region for the Key Vault."
  type        = string
}

variable "tenant_id" {
  description = "Azure Active Directory tenant ID. Used by Key Vault to validate identities. Sourced from the azurerm provider's current client config."
  type        = string
}

variable "soft_delete_retention_days" {
  description = "Number of days to retain deleted vault and secrets. Azure enforces a minimum of 7 days and a maximum of 90 days."
  type        = number
  default     = 7

  validation {
    condition     = var.soft_delete_retention_days >= 7 && var.soft_delete_retention_days <= 90
    error_message = "soft_delete_retention_days must be between 7 and 90 (Azure-enforced range)."
  }
}

variable "tags" {
  description = "Tags applied to all Key Vault resources."
  type        = map(string)
  default     = {}
}
