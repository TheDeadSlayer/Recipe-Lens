# ---------------------------------------------------------------------------
# Private DNS Zone for PostgreSQL Flexible Server VNet integration
#
# Flexible Server VNet-integrated deployments require a private DNS zone
# whose name ends with .postgres.database.azure.com. The zone name does NOT
# have to be exactly <server-name>.private.postgres.database.azure.com;
# Azure accepts any valid subdomain under postgres.database.azure.com
# (e.g. privatelink.postgres.database.azure.com is also supported).
# Using the server-name prefix here keeps each server's zone clearly scoped
# and avoids conflicts between servers in the same subscription.
#
# The server FQDN is taken directly from azurerm_postgresql_flexible_server
# .this.fqdn — it is not constructed from the zone name. The zone merely
# provides private DNS resolution within the VNet.
# ---------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "postgres" {
  name                = "${var.server_name}.private.postgres.database.azure.com"
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# ---------------------------------------------------------------------------
# VNet link — connects the private DNS zone to the VNet so that any resource
# in the VNet (including AKS pods) can resolve the PostgreSQL FQDN.
# registration_enabled = false: the DNS zone is used for resolution only;
# auto-registration of VNet resources is not needed here.
# ---------------------------------------------------------------------------
resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${var.server_name}-dns-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = var.virtual_network_id
  registration_enabled  = false

  tags = var.tags
}

# ---------------------------------------------------------------------------
# PostgreSQL Flexible Server
#
# Networking mode: VNet integration (private-only).
#   delegated_subnet_id  — subnet pre-delegated to
#                          Microsoft.DBforPostgreSQL/flexibleServers
#   private_dns_zone_id  — zone created above; must exist before the server
#   public_network_access_enabled = false — no public endpoint
#
# Authentication: password-only (no Entra ID / AAD auth) because the
# RecipeLens application consumes a standard DATABASE_URL connection string.
# The password is passed via var.administrator_password which uses the
# write-only attribute administrator_password_wo, so it is NEVER written to
# Terraform state.
#
# SKU: B_Standard_B1ms — Burstable tier, 1 vCPU, 2 GB RAM.
#   AzureRM format: <TierPrefix>_<VMSku>. B=Burstable, GP=GeneralPurpose.
#   - Cheapest available SKU for Canada Central.
#   - Appropriate for a dev/interview RecipeLens workload.
#   - Upgrade to GP_Standard_D2ads_v5 for staging/production.
#
# PostgreSQL version: 17 — deliberately chosen as a mature, fully supported
# GA release. Azure Flexible Server also supports 18 (newest) and 16 (LTS).
# Storage: 32 GB (minimum supported, P4 tier, 120 IOPS).
# HA: disabled — single node for dev, no standby replica.
# Geo-redundant backup: disabled — dev only.
# ---------------------------------------------------------------------------
resource "azurerm_postgresql_flexible_server" "this" {
  name                = var.server_name
  resource_group_name = var.resource_group_name
  location            = var.location

  version  = var.postgresql_version
  sku_name = var.sku_name

  # VNet-integrated private networking — no public endpoint.
  delegated_subnet_id           = var.delegated_subnet_id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false

  administrator_login = var.administrator_login

  # administrator_password_wo is a write-only attribute (Terraform 1.11+).
  # The value is sent to Azure at apply time but is NEVER persisted in
  # Terraform state or plan output. This is categorically different from
  # administrator_password (sensitive=true), which IS stored in state and
  # can be recovered with `terraform show`. Always use _wo for secrets.
  #
  # administrator_password_wo_version is a change-detection token. Terraform
  # only re-sends the password to Azure when this number changes. Increment
  # var.administrator_password_version deliberately when rotating the password.
  administrator_password_wo         = var.administrator_password
  administrator_password_wo_version = var.administrator_password_version

  storage_mb = var.storage_mb

  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = false

  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }

  # The DNS zone and VNet link must exist before the server is provisioned,
  # because Azure registers the server FQDN in the zone during creation.
  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.postgres,
  ]

  # Azure automatically assigns (and may update) the availability zone for
  # Flexible Server — Terraform did not originally select a zone, but Azure
  # reports one in the API response. ignore_changes prevents Terraform from
  # treating the Azure-assigned zone as configuration drift and issuing an
  # unrelated update on every plan.
  # Reference: https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle
  lifecycle {
    ignore_changes = [zone]
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Application database
#
# Creates the 'recipelens' database on the server.
# Schema migrations (Alembic) will be run separately as a Kubernetes/Helm
# pre-install Job using: backend image, args: ["migrate"]
# ---------------------------------------------------------------------------
resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
