resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  # Admin credentials are disabled; AcrPull/AcrPush assignments use Entra ID RBAC.
  # The AcrPull assignment for the AKS kubelet identity will be created in the
  # AKS module once the managed identity exists.
  admin_enabled = false

  tags = var.tags
}
