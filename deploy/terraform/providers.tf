terraform {
  required_version = ">= 1.7.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.116"
    }
  }

  # Backend remoto (Azure Storage) fica comentado até existir uma storage
  # account dedicada para state — decisão consciente para não bloquear o
  # primeiro `terraform init` num recurso que ainda não existe.
  # backend "azurerm" {
  #   resource_group_name  = "rg-revold-tfstate"
  #   storage_account_name = "revoldtfstate"
  #   container_name       = "tfstate"
  #   key                  = "revold.tfstate"
  # }
}

provider "azurerm" {
  features {}
}
