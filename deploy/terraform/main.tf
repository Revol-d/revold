module "network" {
  source       = "./modules/network"
  project_name = var.project_name
  environment  = var.environment
  location     = var.location
}

module "key_vault" {
  source              = "./modules/key-vault"
  project_name        = var.project_name
  environment         = var.environment
  location            = module.network.location
  resource_group_name = module.network.resource_group_name
}

module "azure_sql" {
  source              = "./modules/azure-sql"
  project_name        = var.project_name
  environment         = var.environment
  location            = module.network.location
  resource_group_name = module.network.resource_group_name
  admin_password      = var.azure_sql_admin_password
}

module "container_apps" {
  source                   = "./modules/container-apps"
  project_name             = var.project_name
  environment              = var.environment
  location                 = module.network.location
  resource_group_name      = module.network.resource_group_name
  container_apps_subnet_id = module.network.container_apps_subnet_id
  workload_identity_id     = module.key_vault.workload_identity_id
}

module "azure_openai" {
  source                         = "./modules/azure-openai"
  project_name                   = var.project_name
  environment                    = var.environment
  location                       = module.network.location
  resource_group_name            = module.network.resource_group_name
  key_vault_id                   = module.key_vault.key_vault_id
  workload_identity_principal_id = module.key_vault.workload_identity_principal_id
}
