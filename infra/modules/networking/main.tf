resource "azurerm_virtual_network" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space

  tags = var.tags
}

resource "azurerm_subnet" "aks" {
  name                 = var.aks_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = var.aks_subnet_prefixes
}

resource "azurerm_subnet" "postgres" {
  name                 = var.postgres_subnet_name
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = var.postgres_subnet_prefixes

  # Microsoft.Storage service endpoint is automatically added by Azure when a
  # PostgreSQL Flexible Server is deployed into a delegated subnet. Microsoft
  # explicitly documents that removing this endpoint may disrupt core service
  # operations (backup, PITR, logging). Declare it here so Terraform considers
  # it intentional and does not attempt to remove it on every plan.
  # Reference: https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-networking-private
  service_endpoints = ["Microsoft.Storage"]

  delegation {
    name = "postgres-flexible-server"

    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"

      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action"
      ]
    }
  }
}