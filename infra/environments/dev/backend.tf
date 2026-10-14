terraform {
  backend "azurerm" {
    resource_group_name  = "recipelens-bootstrap-rg"
    storage_account_name = "recipelensbootstm7k2"
    container_name       = "tfstate"
    key                  = "recipelens/dev/terraform.tfstate"

    use_azuread_auth = true
    use_cli          = true
  }
}