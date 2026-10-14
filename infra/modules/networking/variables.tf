variable "name" {
  description = "Name of the Azure Virtual Network."
  type        = string
}

variable "resource_group_name" {
  description = "Resource Group containing the Virtual Network."
  type        = string
}

variable "location" {
  description = "Azure region for the Virtual Network."
  type        = string
}

variable "address_space" {
  description = "CIDR address spaces assigned to the Virtual Network."
  type        = list(string)
}

variable "aks_subnet_name" {
  description = "Name of the AKS subnet."
  type        = string
}

variable "aks_subnet_prefixes" {
  description = "CIDR prefixes assigned to the AKS subnet."
  type        = list(string)
}

variable "postgres_subnet_name" {
  description = "Name of the PostgreSQL Flexible Server subnet."
  type        = string
}

variable "postgres_subnet_prefixes" {
  description = "CIDR prefixes assigned to the PostgreSQL subnet."
  type        = list(string)
}

variable "tags" {
  description = "Tags applied to networking resources."
  type        = map(string)
  default     = {}
}