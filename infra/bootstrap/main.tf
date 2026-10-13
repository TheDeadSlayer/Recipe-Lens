locals {
  resource_group_name = "${var.project}-${var.environment}-rg"

  storage_env_slug = substr(replace(var.environment, "-", ""), 0, 6)
  storage_name     = "${var.project}${local.storage_env_slug}${var.suffix}"

  container_name = "tfstate"
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "tfstate" {
  name     = local.resource_group_name
  location = var.location

  tags = {
    application = "RecipeLens"
    environment = var.environment
    managed_by  = "terraform"
    purpose     = "terraform-state"
  }
}

resource "azurerm_storage_account" "tfstate" {
  name                = local.storage_name
  resource_group_name = azurerm_resource_group.tfstate.name
  location            = azurerm_resource_group.tfstate.location

  account_tier             = "Standard"
  account_replication_type = "LRS"

  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = var.shared_access_key_enabled

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = {
    application = "RecipeLens"
    environment = var.environment
    managed_by  = "terraform"
    purpose     = "terraform-state"
  }
}

resource "azurerm_storage_container" "tfstate" {
  name                  = local.container_name
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "tfstate_contributor" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}