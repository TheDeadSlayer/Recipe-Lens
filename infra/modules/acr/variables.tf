variable "name" {
  description = "Name of the Azure Container Registry. Must be globally unique, alphanumeric only, 5–50 chars."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group containing the ACR."
  type        = string
}

variable "location" {
  description = "Azure region for the ACR."
  type        = string
}

variable "sku" {
  description = "ACR SKU (Basic, Standard, Premium)."
  type        = string
  default     = "Basic"
}

variable "tags" {
  description = "Tags applied to the ACR."
  type        = map(string)
  default     = {}
}
