# ---------------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------------

# Current Azure AD tenant — required for Key Vault's tenant_id argument.
data "azurerm_client_config" "current" {}

locals {
  resource_group_name = "${var.project}-${var.environment}-rg"

  vnet_name            = "${var.project}-${var.environment}-vnet"
  aks_subnet_name      = "${var.project}-${var.environment}-aks-snet"
  postgres_subnet_name = "${var.project}-${var.environment}-postgres-snet"

  # Globally-unique resource names derived from project + environment + suffix.
  acr_name     = "${var.project}${var.environment}${var.suffix}acr"
  law_name     = "${var.project}-${var.environment}-law"
  aks_name     = "${var.project}-${var.environment}-aks"
  amw_name     = "${var.project}-${var.environment}-amw"
  grafana_name = "${var.project}-${var.environment}-grafana"
  # PostgreSQL: project-environment-suffix-pg (e.g. recipelens-dev-m7k2-pg)
  # Rules: 3-63 chars, lowercase letters/numbers/hyphens, globally unique.
  pg_server_name = "${var.project}-${var.environment}-${var.suffix}-pg"

  # Key Vault: project-environment-suffix-kv (e.g. recipelens-dev-m7k2-kv)
  # Rules: 3-24 chars, alphanumeric + hyphens, start with letter, globally unique.
  kv_name = "${var.project}-${var.environment}-${var.suffix}-kv"

  # Workload identity: project-environment-app-identity
  workload_identity_name       = "${var.project}-${var.environment}-app-identity"
  workload_federated_cred_name = "${var.project}-${var.environment}-backend-fedcred"

  # PostgreSQL FQDN for secret documentation purposes.
  # The actual DATABASE_URL is inserted post-apply via az keyvault secret set.
  # Format: postgresql://<user>:<pass>@<fqdn>:5432/<db>?sslmode=require
  # FQDN:   recipelens-dev-m7k2-pg.postgres.database.azure.com
  # Key Vault secret names consumed by the RecipeLens backend:
  #   database-url  → DATABASE_URL env var (postgresql://...?sslmode=require)
  #   gemini-api-key → GEMINI_API_KEY env var
  #
  # Insert after apply:
  #   az keyvault secret set --vault-name recipelens-dev-m7k2-kv \
  #     --name database-url \
  #     --value "postgresql://<user>:<pass>@recipelens-dev-m7k2-pg.postgres.database.azure.com:5432/recipelens?sslmode=require"
  #   az keyvault secret set --vault-name recipelens-dev-m7k2-kv \
  #     --name gemini-api-key \
  #     --value "<your-gemini-api-key>"

  common_tags = {
    application = "RecipeLens"
    environment = var.environment
    managed_by  = "terraform"
    project     = var.project
  }
}

module "resource_group" {
  source = "../../modules/resource-group"

  name     = local.resource_group_name
  location = var.location
  tags     = local.common_tags
}

module "networking" {
  source = "../../modules/networking"

  name                = local.vnet_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location

  address_space = var.vnet_address_space

  aks_subnet_name     = local.aks_subnet_name
  aks_subnet_prefixes = var.aks_subnet_prefixes

  postgres_subnet_name     = local.postgres_subnet_name
  postgres_subnet_prefixes = var.postgres_subnet_prefixes

  tags = local.common_tags
}

module "acr" {
  source = "../../modules/acr"

  name                = local.acr_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  sku                 = "Basic"

  tags = local.common_tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  name                = local.law_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  retention_in_days   = 30

  tags = local.common_tags
}

module "aks" {
  source = "../../modules/aks"

  name                = local.aks_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location

  kubernetes_version = var.kubernetes_version
  node_vm_size       = var.node_vm_size
  node_count         = var.node_count

  aks_subnet_id              = module.networking.aks_subnet_id
  acr_id                     = module.acr.id
  log_analytics_workspace_id = module.monitoring.id

  managed_prometheus_enabled = true

  # Key Vault Secrets Store CSI add-on — in-place update to the existing cluster.
  key_vault_csi_enabled           = true
  key_vault_csi_rotation_interval = "2m"

  pod_cidr       = var.pod_cidr
  service_cidr   = var.service_cidr
  dns_service_ip = var.dns_service_ip

  tags = local.common_tags
}

module "observability" {
  source = "../../modules/observability"

  resource_group_name = module.resource_group.name
  location            = module.resource_group.location

  aks_cluster_id = module.aks.cluster_id

  amw_name     = local.amw_name
  grafana_name = local.grafana_name

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Azure Key Vault
# ---------------------------------------------------------------------------

module "key_vault" {
  source = "../../modules/key-vault"

  name                = local.kv_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location

  # Tenant ID from the currently-authenticated Azure session.
  tenant_id = data.azurerm_client_config.current.tenant_id

  soft_delete_retention_days = 7

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# RecipeLens workload identity + federated credential + Key Vault RBAC
# ---------------------------------------------------------------------------

module "workload_identity" {
  source = "../../modules/workload-identity"

  name                = local.workload_identity_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location

  federated_credential_name  = local.workload_federated_cred_name
  oidc_issuer_url            = module.aks.oidc_issuer_url
  kubernetes_namespace       = "recipelens"
  kubernetes_service_account = "recipelens-backend"

  key_vault_id = module.key_vault.key_vault_id

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

module "postgresql" {
  source = "../../modules/postgresql"

  server_name         = local.pg_server_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location

  delegated_subnet_id = module.networking.postgres_subnet_id
  virtual_network_id  = module.networking.vnet_id

  administrator_login            = var.pg_administrator_login
  administrator_password         = var.pg_administrator_password
  administrator_password_version = var.pg_administrator_password_version

  postgresql_version    = var.postgresql_version
  sku_name              = var.pg_sku_name
  storage_mb            = var.pg_storage_mb
  backup_retention_days = var.pg_backup_retention_days
  database_name         = var.pg_database_name

  tags = local.common_tags
}
