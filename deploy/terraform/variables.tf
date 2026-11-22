variable "project_name" {
  type    = string
  default = "revold"
}

variable "environment" {
  type        = string
  description = "dev | staging | production"
  default     = "dev"
}

variable "location" {
  type    = string
  default = "brazilsouth"
}

variable "azure_sql_admin_password" {
  type        = string
  sensitive   = true
  description = "Senha do usuário administrador do Azure SQL Database. Passar via TF_VAR_azure_sql_admin_password, nunca commitar."
}
