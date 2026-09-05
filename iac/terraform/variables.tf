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

variable "postgres_admin_password" {
  type      = string
  sensitive = true
  description = "Senha do usuário administrador do Postgres. Passar via TF_VAR_postgres_admin_password, nunca commitar."
}
