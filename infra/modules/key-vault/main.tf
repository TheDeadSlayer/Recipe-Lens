# ---------------------------------------------------------------------------
# Azure Key Vault
#
# Authorization model: Azure RBAC (rbac_authorization_enabled = true).
#   Access policies are NOT used. Role assignments are made separately via
#   azurerm_role_assignment resources so that least-privilege can be enforced
#   per identity at the Key Vault scope.
#
# Soft delete: enabled (always on in Azure; provider controls retention days).
#   Minimum Azure-enforced retention is 7 days.
# Purge protection: disabled for dev — enables faster destroy/recreate cycles.
#   Enable in staging/production to prevent accidental permanent deletion.
#
# Network access: public (no private endpoint in this stage).
#   A private endpoint will be evaluated in a later stage once VNet
#   integration patterns are validated.
#
# SKU: standard — sufficient for secret storage.
#   premium is required only for HSM-backed keys.
# ---------------------------------------------------------------------------
resource "azurerm_key_vault" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location

  tenant_id = var.tenant_id
  sku_name  = "standard"

  # Azure RBAC authorization — role assignments control all access.
  # Access policies (legacy model) are intentionally not used.
  rbac_authorization_enabled = true

  # Soft delete: Azure enforces a minimum of 7 days.
  soft_delete_retention_days = var.soft_delete_retention_days

  # Purge protection disabled for dev: allows vault deletion without a
  # mandatory retention wait. Must be enabled for production vaults.
  purge_protection_enabled = false

  # Public network access: enabled in this stage.
  # The CSI driver pods running on AKS will reach the vault over the
  # public endpoint. A private endpoint can be added in a later stage.
  public_network_access_enabled = true

  tags = var.tags
}
