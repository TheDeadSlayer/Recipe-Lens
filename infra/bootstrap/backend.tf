terraform {
  backend "azurerm" {
    storage_account_name = "recipelensbootstm7k2"
    container_name       = "tfstate"
    key                  = "recipelens/bootstrap/terraform.tfstate"

    use_azuread_auth = true
    use_cli          = true
  }
}