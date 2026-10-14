variable "name" {
  description = "Name of the Log Analytics Workspace."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group containing the Log Analytics Workspace."
  type        = string
}

variable "location" {
  description = "Azure region for the Log Analytics Workspace."
  type        = string
}

variable "sku" {
  description = "Log Analytics Workspace SKU."
  type        = string
  default     = "PerGB2018"
}

variable "retention_in_days" {
  description = "Data retention period in days (30–730)."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags applied to the Log Analytics Workspace."
  type        = map(string)
  default     = {}
}
