# ---------------------------------------------------------------------------
# RecipeLens workload user-assigned managed identity (UAMI)
#
# This identity represents the RecipeLens backend application workload.
# It is distinct from:
#   - The AKS control-plane UAMI  (cluster Azure operations)
#   - The AKS kubelet identity     (ACR pulls, node-level ops)
#   - The Key Vault CSI add-on identity (auto-created by Azure in MC_... RG)
#
# The workload UAMI is used exclusively by the RecipeLens backend Pod through
# the AKS Workload Identity / OIDC federation mechanism. The Pod's Kubernetes
# ServiceAccount carries an annotation referencing this UAMI's client_id, and
# Pods using that ServiceAccount carry the label:
#   azure.workload.identity/use: "true"
# ---------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "workload" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Federated Identity Credential
#
# Binds the Kubernetes ServiceAccount to the UAMI via the AKS OIDC issuer.
#
# The federated subject MUST exactly match:
#   system:serviceaccount:<namespace>:<service-account-name>
#
# Azure AD token exchange flow:
#   1. Pod requests a projected ServiceAccount token (audience: api://AzureADTokenExchange)
#   2. AKS injects the token at the projected volume path
#   3. The Azure Identity SDK exchanges the SA token for an Azure AD token
#      by calling the OIDC endpoint at var.oidc_issuer_url
#   4. Azure AD validates the issuer, subject, and audience against this FIC
#   5. An Azure AD access token is returned, scoped to the UAMI
#
# The Kubernetes ServiceAccount does not need to exist before this credential
# is created. FIC registration is purely an Azure AD / ARM operation.
#
# AzureRM 4.x uses `user_assigned_identity_id` (the non-deprecated field).
# `parent_id` and `resource_group_name` on this resource are deprecated in
# AzureRM 4.x and will be removed in v5.0 — they are intentionally omitted.
# ---------------------------------------------------------------------------
resource "azurerm_federated_identity_credential" "workload" {
  name                      = var.federated_credential_name
  user_assigned_identity_id = azurerm_user_assigned_identity.workload.id

  issuer  = var.oidc_issuer_url
  subject = "system:serviceaccount:${var.kubernetes_namespace}:${var.kubernetes_service_account}"

  # Microsoft-recommended audience for AKS Workload Identity federation.
  # The Azure Identity SDK and the OIDC token issuer both use this value.
  # Reference: https://learn.microsoft.com/azure/aks/workload-identity-overview
  audience = ["api://AzureADTokenExchange"]
}

# ---------------------------------------------------------------------------
# Key Vault Secrets User — scoped to the RecipeLens Key Vault only.
#
# Role: Key Vault Secrets User (built-in)
#   Allows: secrets/getSecret, secrets/list (read-only on secret VALUES)
#   Denies: secrets/set, secrets/delete, secrets/backup, secrets/purge
#
# This is the minimum role required for the CSI driver to retrieve secret
# values on behalf of the workload UAMI.
#
# Reference:
#   https://learn.microsoft.com/azure/key-vault/general/rbac-guide
#   Role definition ID: 4633458b-17de-408a-b874-0445c86b69e6
# ---------------------------------------------------------------------------
resource "azurerm_role_assignment" "workload_kv_secrets_user" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.workload.principal_id
}
