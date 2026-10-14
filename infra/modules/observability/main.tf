# ---------------------------------------------------------------------------
# Azure Monitor Workspace (managed Prometheus back-end)
#
# Receives Prometheus metrics scraped from AKS via an explicit DCR/DCRA
# pipeline. Azure also auto-creates a platform-managed DCR and DCE in a
# managed resource group named MA_<workspace>_<location>_managed when
# monitor_metrics is enabled on AKS; those platform resources are separate
# from the ones below and must not be imported or recreated here.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_workspace" "this" {
  name                = var.amw_name
  resource_group_name = var.resource_group_name
  location            = var.location

  # Public query endpoint — acceptable for dev. Use private link for prod.
  public_network_access_enabled = true

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Data Collection Endpoint (DCE)
#
# A DCE is required as the ingestion gateway for the Prometheus DCR.
# kind = "Linux" matches AKS Linux node pools.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_endpoint" "prometheus" {
  name                = "${var.amw_name}-dce"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "Linux"

  # Public ingestion — acceptable for dev. Disable for production.
  public_network_access_enabled = true

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Data Collection Rule (DCR)
#
# Wires the Prometheus forwarder agent running on AKS nodes to the Azure
# Monitor Workspace. The rule:
#   data_sources.prometheus_forwarder — collects Microsoft-PrometheusMetrics
#   destinations.monitor_account      — targets the AMW
#   data_flow                          — routes stream → destination
#
# kind = "Linux" is required when data_sources contains prometheus_forwarder.
# data_collection_endpoint_id links the DCR to the DCE above.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_rule" "prometheus" {
  name                        = "${var.amw_name}-dcr"
  resource_group_name         = var.resource_group_name
  location                    = var.location
  kind                        = "Linux"
  data_collection_endpoint_id = azurerm_monitor_data_collection_endpoint.prometheus.id

  data_sources {
    prometheus_forwarder {
      name    = "PrometheusDataSource"
      streams = ["Microsoft-PrometheusMetrics"]
    }
  }

  destinations {
    monitor_account {
      monitor_account_id = azurerm_monitor_workspace.this.id
      name               = "MonitoringAccount"
    }
  }

  data_flow {
    streams      = ["Microsoft-PrometheusMetrics"]
    destinations = ["MonitoringAccount"]
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Data Collection Rule Association (DCRA)
#
# Associates the Prometheus DCR with the AKS cluster resource so the
# metrics add-on agent knows which rule governs its scraping behaviour.
# target_resource_id must be the AKS managed cluster resource ID.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_rule_association" "aks_prometheus" {
  name                    = "${var.amw_name}-dcra"
  target_resource_id      = var.aks_cluster_id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.prometheus.id
}

# ---------------------------------------------------------------------------
# Azure Managed Grafana
#
# SKU:                 Standard (required for Azure Monitor integration)
# SKU size:            X1 — single replica, cost-optimal for dev
# Grafana version:     12 (current GA major version; v11 retired June 2026)
# Identity:            System-assigned — required for AMW RBAC
# Zone redundancy:     Disabled — unnecessary for dev
# API keys:            Disabled (Entra ID auth only)
# Public access:       Enabled — acceptable for dev
#
# azure_monitor_workspace_integrations wires the Grafana data source plugin
# directly to the AMW Prometheus query endpoint.
# ---------------------------------------------------------------------------
resource "azurerm_dashboard_grafana" "this" {
  name                = var.grafana_name
  resource_group_name = var.resource_group_name
  location            = var.location

  grafana_major_version = var.grafana_major_version # "12" set in variables.tf

  sku                           = "Standard"
  zone_redundancy_enabled       = false
  public_network_access_enabled = true
  api_key_enabled               = false

  identity {
    type = "SystemAssigned"
  }

  azure_monitor_workspace_integrations {
    resource_id = azurerm_monitor_workspace.this.id
  }

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Monitoring Data Reader — grant Grafana's system-assigned identity
# permission to query Prometheus metrics from the Azure Monitor Workspace.
#
# "Monitoring Data Reader" is the Microsoft-documented built-in role for
# Azure Managed Grafana querying Prometheus data from an AMW.
# Scoped specifically to this AMW resource, not the RG or subscription.
# See: https://learn.microsoft.com/azure/managed-grafana/how-to-permissions
# ---------------------------------------------------------------------------
resource "azurerm_role_assignment" "grafana_amw_monitoring_data_reader" {
  scope                = azurerm_monitor_workspace.this.id
  role_definition_name = "Monitoring Data Reader"
  principal_id         = azurerm_dashboard_grafana.this.identity[0].principal_id
}
