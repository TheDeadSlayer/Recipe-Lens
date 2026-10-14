output "key_vault_id" {
  description = "Resource ID of the Azure Key Vault."
  value       = azurerm_key_vault.this.id
}

output "key_vault_name" {
  description = "Name of the Azure Key Vault."
  value       = azurerm_key_vault.this.name
}

output "key_vault_uri" {
  description = "URI of the Azure Key Vault (used by the CSI driver SecretProviderClass)."
  value       = azurerm_key_vault.this.vault_uri
}
