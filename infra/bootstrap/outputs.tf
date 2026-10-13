output "resource_group_name" {
  description = "Resource group containing Terraform remote state infrastructure."
  value       = azurerm_resource_group.tfstate.name
}

output "storage_account_name" {
  description = "Storage Account used for Terraform remote state."
  value       = azurerm_storage_account.tfstate.name
}

output "container_name" {
  description = "Blob container used for Terraform state."
  value       = azurerm_storage_container.tfstate.name
}

output "operator_object_id" {
  description = "Entra ID object ID granted access to Terraform state."
  value       = data.azurerm_client_config.current.object_id
}