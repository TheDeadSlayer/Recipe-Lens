variable "project" {
  description = "Project name used for Azure resource naming."
  type        = string
  default     = "recipelens"

  validation {
    condition     = can(regex("^[a-z0-9]+$", var.project))
    error_message = "project must contain only lowercase letters and numbers."
  }
}

variable "environment" {
  description = "Environment name for the bootstrap resources."
  type        = string
  default     = "bootstrap"
}

variable "location" {
  description = "Azure region where Terraform state infrastructure will be created."
  type        = string
  default     = "canadacentral"
}

variable "suffix" {
  description = "Stable 4-6 character lowercase alphanumeric suffix used for globally unique resource names."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{4,6}$", var.suffix))
    error_message = "suffix must be 4-6 lowercase alphanumeric characters."
  }
}

variable "shared_access_key_enabled" {
  description = "Temporary bootstrap setting. Leave true for Phase 1, then set false after Entra ID RBAC and remote state are configured."
  type        = bool
  default     = false
}