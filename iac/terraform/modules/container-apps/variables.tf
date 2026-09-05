variable "project_name"             { type = string }
variable "environment"              { type = string }
variable "location"                 { type = string }
variable "resource_group_name"      { type = string }
variable "container_apps_subnet_id" { type = string }
variable "workload_identity_id"     { type = string }

variable "database_url_placeholder" {
  type        = string
  sensitive   = true
  description = "Placeholder — em produção isto vem do Key Vault via referência de secret, não de uma variável Terraform em texto plano."
  default     = ""
}
