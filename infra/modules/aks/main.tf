# ---------------------------------------------------------------------------
# Control-plane user-assigned managed identity (UAMI)
#
# AKS uses this identity for Azure control-plane operations: attaching NICs
# to the BYO subnet, managing the public load balancer, reading VNet metadata.
# A UAMI is required (rather than system-assigned) when the cluster uses a
# pre-existing BYO subnet, because the identity must exist before the cluster
# is created so that Network Contributor can be granted in advance.
# ---------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "aks_control_plane" {
  name                = "${var.name}-cp-identity"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Network Contributor on the AKS subnet — scoped tightly to the one subnet.
#
# Required so the AKS control plane can attach node NICs, configure routes,
# and manage the subnet during cluster provisioning and upgrades.
# ---------------------------------------------------------------------------
resource "azurerm_role_assignment" "aks_cp_network_contributor" {
  scope                = var.aks_subnet_id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks_control_plane.principal_id
}

# ---------------------------------------------------------------------------
# AKS managed cluster
#
# Identity model:
#   Control-plane UAMI  → cluster Azure operations (subnet/NIC/LB management)
#   Kubelet identity    → node-level ops: ACR image pulls, kubelet Azure calls
#   Workload Identity   → future per-Pod identity via OIDC + ServiceAccount
#                         federation (no federated credentials created here)
#
# NODE OS: Ubuntu2404 — explicit current-generation Ubuntu LTS.
# "Ubuntu" (bare alias) is avoided because it resolves ambiguously across
# AKS versions. AzureLinux / AzureLinux3 support for ARM64 on 1.36 was not
# verified in this subscription, so Ubuntu2404 is the safe explicit choice.
#
# ARM64 NOTE: Standard_D2pds_v5 is an Ampere Altra ARM64 SKU. All RecipeLens
# container images must be built for linux/arm64 or as multi-platform
# linux/amd64,linux/arm64 manifests before application deployment to this
# cluster. Single-platform linux/amd64 images will not run on these nodes.
# ---------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  kubernetes_version  = var.kubernetes_version
  dns_prefix          = var.name

  # User-assigned managed identity for the AKS control plane.
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_control_plane.id]
  }

  # ---------------------------------------------------------------------------
  # Default (system) node pool
  # ---------------------------------------------------------------------------
  default_node_pool {
    name           = "system"
    node_count     = var.node_count
    vm_size        = var.node_vm_size
    vnet_subnet_id = var.aks_subnet_id

    # Explicit OS SKU — Ubuntu 24.04 LTS, current supported generation.
    os_sku = "Ubuntu2404"

    # Pin the Kubernetes version on the node pool to match the cluster.
    orchestrator_version = var.kubernetes_version

    # Upgrade settings required by AzureRM 4.x when orchestrator_version is set.
    upgrade_settings {
      max_surge = "10%"
    }
  }

  # ---------------------------------------------------------------------------
  # Networking — Azure CNI Overlay with Cilium data plane
  # ---------------------------------------------------------------------------
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    pod_cidr            = var.pod_cidr
    service_cidr        = var.service_cidr
    dns_service_ip      = var.dns_service_ip
  }

  # ---------------------------------------------------------------------------
  # OIDC issuer + Workload Identity
  # ---------------------------------------------------------------------------
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # ---------------------------------------------------------------------------
  # Azure Key Vault Secrets Store CSI provider
  #
  # Installs the Secrets Store CSI driver + Azure Key Vault provider add-on
  # on every node. This is an IN-PLACE cluster update (~ not -/+).
  #
  # secret_rotation_enabled  = true  — the CSI driver periodically polls Key
  #   Vault and refreshes mounted secrets without restarting Pods. Combined
  #   with a SecretProviderClass sync to a Kubernetes Secret, this allows
  #   Pods to pick up rotated secrets on the next container restart or within
  #   the rotation interval.
  # secret_rotation_interval = "2m"  — poll interval for dev. Production
  #   workloads should use a longer interval (e.g. "1h") to reduce API calls.
  #
  # Note: Azure automatically creates a separate managed identity for the CSI
  # add-on in the node resource group (MC_...). This is expected behaviour
  # documented by Microsoft — it cannot be suppressed. That identity is used
  # by the driver agent itself and is NOT the RecipeLens application identity.
  # The RecipeLens workload uses its own UAMI via Workload Identity (OIDC).
  # Reference:
  #   https://learn.microsoft.com/azure/aks/csi-secrets-store-driver
  # ---------------------------------------------------------------------------
  dynamic "key_vault_secrets_provider" {
    for_each = var.key_vault_csi_enabled ? [1] : []
    content {
      secret_rotation_enabled  = true
      secret_rotation_interval = var.key_vault_csi_rotation_interval
    }
  }

  # ---------------------------------------------------------------------------
  # Monitoring — Container Insights logs → existing Log Analytics Workspace
  # ---------------------------------------------------------------------------
  oms_agent {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }

  # ---------------------------------------------------------------------------
  # Managed Prometheus add-on
  #
  # Enabling this block installs the metrics add-on agent on every node.
  # Azure automatically creates a platform-managed DCR and DCE in a managed
  # resource group named MA_<workspace>_<location>_managed — do not import
  # or recreate those resources here.
  # Routing to the custom Azure Monitor Workspace is handled by the explicit
  # DCR/DCRA created in the observability module, not by this block.
  # annotations_allowed / labels_allowed default to null (pass all through).
  # ---------------------------------------------------------------------------
  dynamic "monitor_metrics" {
    for_each = var.managed_prometheus_enabled ? [1] : []
    content {}
  }

  # The control-plane UAMI must hold Network Contributor on the subnet before
  # AKS provisioning begins. Explicit depends_on enforces this ordering even
  # though the identity_ids reference already creates an implicit dependency on
  # the UAMI itself — the role assignment is a separate resource.
  depends_on = [
    azurerm_role_assignment.aks_cp_network_contributor,
  ]

  tags = var.tags
}

# ---------------------------------------------------------------------------
# AcrPull — grant the AKS kubelet identity pull access to the ACR.
#
# The kubelet identity is an AKS-managed user-assigned managed identity
# shared across all nodes in the cluster/node pool. AKS auto-creates it in
# the node resource group (MC_...) when no pre-existing kubelet identity is
# supplied. It is used for:
#   - pulling container images from ACR at runtime
#   - kubelet Azure API calls on behalf of the node pool
#
# ACR roleAssignmentMode is "LegacyRegistryPermissions" (verified), so the
# standard AcrPull role assignment is the correct mechanism. If the ACR were
# switched to ABAC mode this assignment would need to be reviewed.
#
# This is NOT the Workload Identity / OIDC identity — that federation is
# configured separately per workload via ServiceAccount annotations.
# ---------------------------------------------------------------------------
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
}

resource "azurerm_kubernetes_cluster_node_pool" "app" {
  name                  = "app"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id

  vm_size    = "Standard_D2pds_v5"
  node_count = 1
  mode       = "User"

  vnet_subnet_id = var.aks_subnet_id

  os_type = "Linux"
  os_sku  = "Ubuntu"

  tags = var.tags
}