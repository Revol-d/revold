variable "project_name"        { type = string }
variable "environment"         { type = string }
variable "location"            { type = string }
variable "resource_group_name" { type = string }
variable "key_vault_id"        { type = string }

# Principal id (object id) da identidade gerenciada dos serviços — não o
# resource id (ver modules/key-vault outputs.workload_identity_principal_id).
variable "workload_identity_principal_id" { type = string }

variable "chat_deployment_name" {
  type    = string
  default = "gpt-4o-mini"
}
variable "chat_model_name" {
  type    = string
  default = "gpt-4o-mini"
}
variable "chat_model_version" {
  type    = string
  default = "2024-07-18"
}
variable "chat_capacity" {
  type        = number
  default     = 10
  description = "Capacidade em TPM (múltiplos de 1000) do deployment de chat — SKU pequeno, adequado ao volume de um cliente piloto."
}

variable "embedding_deployment_name" {
  type    = string
  default = "text-embedding-3-small"
}
variable "embedding_model_name" {
  type    = string
  default = "text-embedding-3-small"
}
variable "embedding_model_version" {
  type    = string
  default = "1"
}
variable "embedding_capacity" {
  type    = number
  default = 10
}
