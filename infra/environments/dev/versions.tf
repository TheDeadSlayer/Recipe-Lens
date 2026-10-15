terraform {
  # >= 1.11 required for write-only resource attributes (administrator_password_wo).
  # >= 1.10 required for ephemeral input variables.
  required_version = ">= 1.11, < 2.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }

    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }
}